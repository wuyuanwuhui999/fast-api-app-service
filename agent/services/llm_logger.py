# agent/services/llm_logger.py
"""大模型调用观测（只打日志，不改变任何业务行为）。

把每次调用大模型时「发给模型的参数 / 完整提示词 / 模型原始返回 / 工具(SQL)调用」
打印到日志，便于在 launcher 控制台直接查看。

环境变量：
  AGENT_LLM_LOG=0            关闭本模块的所有输出（默认 1 开启）
  AGENT_LLM_LOG_PROMPT_MAX   system/human 消息单条最大打印字符数，0=不截断（默认 0）
  AGENT_LLM_LOG_REPR=0       关闭 message_repr（默认 1 打印 langchain 的消息结构）

用法：
  log_llm_request(stage=..., request_params={...}, model_config=..., show_think=..., messages=[...])
  response = await model.ainvoke(messages, config={"callbacks": [LlmTraceCallback(stage)]})
  log_llm_response(stage=..., response=response, elapsed_ms=123)
  log_tool_plan(result)          # LLM 生成的「工具计划」：search_type / keyword / sql_condition
  log_tool_sql(sql, params, rows) # 真正执行的 SQL（相当于工具调用）
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

try:  # langchain 是 agent 模块的既有依赖，这里仍做降级保护：日志不能拖垮业务
    from langchain_core.callbacks import BaseCallbackHandler as _BaseCallbackHandler  # type: ignore[assignment]
except Exception:  # pragma: no cover
    class _BaseCallbackHandler:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

LINE = "=" * 78


def _enabled() -> bool:
    return os.getenv("AGENT_LLM_LOG", "1") not in ("0", "false", "False", "")


def _prompt_max() -> int:
    try:
        return int(os.getenv("AGENT_LLM_LOG_PROMPT_MAX", "0") or 0)
    except ValueError:
        return 0


def _clip(text: str) -> str:
    limit = _prompt_max()
    if limit and len(text) > limit:
        return f"{text[:limit]}\n... [已截断，共 {len(text)} 字符，AGENT_LLM_LOG_PROMPT_MAX={limit}]"
    return text


def _as_text(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _kv(pairs: Sequence[tuple]) -> str:
    width = max((len(k) for k, _ in pairs), default=0)
    return "\n".join(f"  {k.ljust(width)} : {_as_text(v)}" for k, v in pairs)


def _message_repr(message: Any) -> str:
    """langchain 消息对象 -> 'SystemMessage'/'HumanMessage' 等类名。"""
    return type(message).__name__


def _message_role(message: Any) -> str:
    for attr in ("type", "role"):
        role = getattr(message, attr, None)
        if isinstance(role, str) and role:
            return role
    return "unknown"


def log_llm_request(
        stage: str,
        request_params: Optional[Dict[str, Any]] = None,
        model_config: Any = None,
        show_think: Optional[bool] = None,
        messages: Optional[Iterable[Any]] = None,
) -> None:
    """打印「发给大模型的参数 + 完整提示词(messages)」。"""
    if not _enabled():
        return
    try:
        out: List[str] = [LINE, f"▶ [AgentLLM] 调用大模型  stage={stage}"]
        if request_params:
            out.append("-- 请求参数 " + "-" * 60)
            out.append(_kv(list(request_params.items())))
        if model_config is not None:
            out.append("-- 模型配置 " + "-" * 60)
            out.append(_kv([
                ("type", getattr(model_config, "type", None)),
                ("model_name", getattr(model_config, "model_name", None)),
                ("base_url", getattr(model_config, "base_url", None)),
                ("api_key", "***" if getattr(model_config, "api_key", None) else None),
                ("showThink(reasoning)", show_think),
            ]))
        if messages is not None:
            msgs = list(messages)
            out.append(f"-- 提示词 messages（共 {len(msgs)} 条） " + "-" * 40)
            for i, msg in enumerate(msgs):
                if isinstance(msg, (tuple, list)) and len(msg) == 2:
                    role, content = msg
                    cls = f"{str(role).capitalize()}Message"
                else:
                    role, content, cls = _message_role(msg), getattr(msg, "content", msg), _message_repr(msg)
                out.append(f"  ---- [{i}] {role} ({cls}) ----")
                out.append(_clip(_as_text(content)))
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    out.append(f"  tool_calls: {_as_text(tool_calls)}")
        out.append(LINE)
        logger.info("\n".join(out))
    except Exception as e:  # 日志永远不能影响业务
        logger.warning(f"[AgentLLM] 打印请求日志失败: {e}")


def log_llm_response(stage: str, response: Any, elapsed_ms: Optional[float] = None) -> None:
    """打印「模型原始返回内容」。"""
    if not _enabled():
        return
    try:
        content = getattr(response, "content", response)
        out = [LINE, f"◀ [AgentLLM] 模型返回  stage={stage}"
                      + (f"  耗时={elapsed_ms:.0f}ms" if elapsed_ms is not None else ""),
               "  content: " + _as_text(content)]
        tool_calls = getattr(response, "tool_calls", None)
        out.append(f"  tool_calls: {_as_text(tool_calls) if tool_calls else '无'}")
        meta = getattr(response, "response_metadata", None)
        if meta:
            usage = meta.get("token_usage") or meta.get("usage") or {}
            keep = {
                k: v for k, v in (usage or {}).items()
                if k in ("prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens")
            }
            out.append(f"  token用量: {_as_text(keep) if keep else '未提供'}")
            for k in ("model_name", "finish_reason", "done_reason", "eval_count", "total_duration"):
                if meta.get(k) is not None:
                    out.append(f"  {k}: {_as_text(meta.get(k))}")
        additional = getattr(response, "additional_kwargs", None) or {}
        reasoning = additional.get("reasoning_content") or additional.get("thinking")
        if reasoning:
            out.append(f"  思考内容: {_clip(_as_text(reasoning))}")
        out.append(LINE)
        logger.info("\n".join(out))
    except Exception as e:
        logger.warning(f"[AgentLLM] 打印返回日志失败: {e}")


def log_model_instance(model: Any, stage: str = "") -> None:
    """打印模型实例的『生效参数』（= 真正会发给模型服务端的配置）。"""
    if not _enabled():
        return
    try:
        pairs: List[tuple] = []
        ident = getattr(model, "_identifying_params", None)
        if isinstance(ident, dict):
            for k, v in ident.items():
                if v is not None:
                    pairs.append((k, v))
        for field in ("model", "model_name", "base_url", "temperature", "top_p", "top_k", "num_ctx",
                      "num_predict", "num_gpu", "keep_alive", "repeat_penalty", "repeat_last_n",
                      "seed", "stop", "format", "reasoning", "think", "streaming", "max_tokens",
                      "api_key", "timeout"):
            if field in dict(pairs):
                continue
            value = getattr(model, field, None)
            if value is not None:
                pairs.append((field, "***" if field == "api_key" else value))
        logger.info(
            f"[AgentLLM] 模型实例生效参数  class={type(model).__name__}"
            + (f"  stage={stage}" if stage else "")
            + "\n" + _kv(pairs)
        )
    except Exception as e:
        logger.warning(f"[AgentLLM] 打印模型参数失败: {e}")


def log_tool_plan(intent: Dict[str, Any]) -> None:
    """打印 LLM 生成的「工具计划」：把自然语言翻译成的查询意图 + SQL 条件。"""
    if not _enabled():
        return
    try:
        logger.info(
            "\n".join([
                f"[AgentLLM] 工具调用计划(LLM→SQL查询)  意图="
                f"{_as_text(intent.get('explanation'))}",
                f"          search_type={_as_text(intent.get('search_type'))}  "
                f"search_keyword={_as_text(intent.get('search_keyword'))}",
                f"          sql_condition={_as_text(intent.get('sql_condition'))}  "
                f"join_tables={_as_text(intent.get('join_tables'))}",
            ])
        )
    except Exception as e:
        logger.warning(f"[AgentLLM] 打印工具计划失败: {e}")


def log_tool_sql(sql: str, params: Dict[str, Any], row_count: Optional[int] = None) -> None:
    """打印真正执行的 SQL（本模块的『工具调用』就是数据库查询）。"""
    if not _enabled():
        return
    try:
        logger.info(
            "\n".join([
                "[AgentLLM] 工具调用(数据库查询)",
                f"          params={_as_text(params)}",
                f"          返回行数={row_count if row_count is not None else '?'}",
                "          SQL=" + " ".join(str(sql).split()),
            ])
        )
    except Exception as e:
        logger.warning(f"[AgentLLM] 打印 SQL 日志失败: {e}")


def log_tool_user_status(music_id: Any, is_like: int, is_favorite: int) -> None:
    """打印每个音乐条目的用户状态查询结果（点赞/收藏）。"""
    if not _enabled():
        return
    logger.info(f"[AgentLLM] 工具调用(用户状态) music_id={music_id} 点赞={is_like} 收藏={is_favorite}")


class LlmTraceCallback(_BaseCallbackHandler):
    """langchain 回调：抓模型真实入参/出参（含 invocation_params、token 用量、工具调用）。"""

    def __init__(self, stage: str = "llm"):
        self.stage = stage
        self._start: Dict[str, float] = {}

    # ---- 入参 ----
    def on_chat_model_start(self, serialized, messages, run_id=None, **kwargs):
        self._log_start(serialized, run_id=run_id, messages=messages, **kwargs)

    def on_llm_start(self, serialized, prompts, run_id=None, **kwargs):
        self._log_start(serialized, run_id=run_id, prompts=prompts, **kwargs)

    def _log_start(self, serialized, run_id=None, messages=None, prompts=None, **kwargs):
        if not _enabled():
            return
        try:
            self._start[str(run_id)] = time.perf_counter()
            params = kwargs.get("invocation_params") or {}
            ident = (serialized or {}).get("kwargs") or {}
            out = [
                LINE,
                f"▶ [AgentLLM][callback] 模型真实入参  stage={self.stage}",
                "-- invocation_params " + "-" * 50,
                _kv(list(params.items())),
            ]
            if ident:
                out += ["-- 模型标识(serialized.kwargs) " + "-" * 40,
                        _kv(list(ident.items()))]
            if messages:
                flat = [m for batch in messages for m in batch] if isinstance(messages[0], list) else messages
                out.append(f"-- callback 收到的消息（共 {len(flat)} 条） " + "-" * 30)
                for i, msg in enumerate(flat):
                    out.append(f"  [{i}] {_message_role(msg)} ({_message_repr(msg)}): "
                               f"{_clip(_as_text(getattr(msg, 'content', msg)))}")
            if prompts:
                out.append(f"-- 渲染后的 prompt 字符串（共 {len(prompts)} 条） " + "-" * 25)
                for i, p in enumerate(prompts):
                    out.append(f"  [{i}] {_clip(_as_text(p))}")
            out.append(LINE)
            logger.info("\n".join(out))
        except Exception as e:
            logger.warning(f"[AgentLLM] callback 记录入参失败: {e}")

    # ---- 出参 ----
    def on_llm_new_token(self, token, run_id=None, **kwargs):
        # 流式 token 逐条打印会刷屏，只在出现工具/思考标记时提示
        if _enabled() and token and any(k in str(token) for k in ("<tool", "<think", "```")):
            logger.info(f"[AgentLLM][callback] 流式输出片段: {token!r}")

    def on_llm_end(self, response, run_id=None, **kwargs):
        if not _enabled():
            return
        try:
            elapsed = time.perf_counter() - self._start.pop(str(run_id), time.perf_counter())
            out = [LINE, f"◀ [AgentLLM][callback] 模型返回  stage={self.stage}  耗时={elapsed * 1000:.0f}ms"]
            for gen_list in getattr(response, "generations", []) or []:
                for gen in gen_list:
                    msg = getattr(gen, "message", None)
                    out.append("  content: " + _clip(_as_text(getattr(msg, "content", gen))))
                    calls = getattr(msg, "tool_calls", None)
                    out.append("  tool_calls: " + (_as_text(calls) if calls else "无"))
            llm_output = getattr(response, "llm_output", None) or {}
            if llm_output:
                out.append("  llm_output: " + _as_text(llm_output))
            out.append(LINE)
            logger.info("\n".join(out))
        except Exception as e:
            logger.warning(f"[AgentLLM] callback 记录返回失败: {e}")

    def on_llm_error(self, error, run_id=None, **kwargs):
        logger.error(f"[AgentLLM][callback] 模型调用异常 stage={self.stage}: {type(error).__name__}: {error}")

    # ---- 工具调用（若将来接入 langgraph/langchain tools） ----
    def on_tool_start(self, serialized, input_str, run_id=None, **kwargs):
        if _enabled():
            logger.info(f"[AgentLLM][callback] 工具调用开始 "
                        f"name={(serialized or {}).get('name')} input={_clip(_as_text(input_str))}")

    def on_tool_end(self, output, run_id=None, **kwargs):
        if _enabled():
            logger.info(f"[AgentLLM][callback] 工具调用结束 output={_clip(_as_text(output))}")

    def on_tool_error(self, error, run_id=None, **kwargs):
        logger.error(f"[AgentLLM][callback] 工具调用异常: {type(error).__name__}: {error}")

