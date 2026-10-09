"""agent 模块可调用的工具（收藏夹 / 音乐圈操作）。

与 SQL 查询路径互补：当用户意图**无法提取出音乐查询 SQL** 时（例如「把周杰伦的歌加到大陆男歌手收藏夹」
「创建/删除/重命名收藏夹」「把这首歌分享到音乐圈」），由大模型从下面的工具清单里选一个工具，
再由服务端执行（服务端自己解析「收藏夹名称 -> id」「歌曲名称 -> music_id」）。
选不出任何工具时，agent 统一回复「只能回答与音乐相关的问题」。

工具清单（TOOL_CATALOG）与 Spring Boot 侧 agent 模块保持一致：名称、参数名、语义都要一样。

表结构：
- music_favorite_directory(id, name, user_id, create_time, update_time)
- music_favorite_list(id, music_id, favorite_id, create_time, update_time)  -- favorite_id 外键 ON DELETE CASCADE
- circle(id, relation_id, content, imgs, type, user_id, create_time, update_time, permission)  -- type='MUSIC' 时 relation_id = music.id
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("agent")

# 一屏内的一次性操作最多涉及多少首歌（避免一条指令往收藏夹塞几百首）
MAX_SONGS = 50

TOOL_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "addMusicToFavorite",
        "description": "把歌曲添加到用户的收藏夹（收藏夹不存在时会提示先创建）",
        "params": {
            "favoriteName": "收藏夹名称（必填）",
            "songName": "歌曲名（可选，模糊匹配）",
            "authorName": "歌手名（可选，模糊匹配）",
            "albumName": "专辑名（可选，模糊匹配）",
            "musicIds": "歌曲 id 数组（可选；用户用「这首歌/这些歌」指代上一轮结果时用）",
        },
    },
    {
        "name": "createFavoriteDirectory",
        "description": "创建收藏夹",
        "params": {"name": "收藏夹名称（必填）"},
    },
    {
        "name": "deleteFavoriteDirectory",
        "description": "删除收藏夹，连同收藏夹里的歌曲一起删除",
        "params": {"name": "收藏夹名称（必填）"},
    },
    {
        "name": "renameFavoriteDirectory",
        "description": "修改收藏夹名称",
        "params": {"oldName": "原收藏夹名称（必填）", "newName": "新收藏夹名称（必填）"},
    },
    {
        "name": "shareMusicToCircle",
        "description": "把歌曲分享到音乐圈（发一条音乐朋友圈）",
        "params": {
            "songName": "歌曲名（可选，模糊匹配）",
            "authorName": "歌手名（可选，模糊匹配）",
            "musicIds": "歌曲 id 数组（可选；用户用「这首歌」指代上一轮结果时用）",
            "content": "分享文案（可选，不给则自动生成）",
            "permission": "可见权限：0 不公开 / 1 公开（可选，默认 1）",
        },
    },
]

TOOL_NAMES = [tool["name"] for tool in TOOL_CATALOG]


def render_tool_catalog() -> str:
    """把工具清单渲染成提示词里的文本（两项目格式一致）"""
    lines = []
    for tool in TOOL_CATALOG:
        params = "、".join(f"{k}：{v}" for k, v in tool["params"].items())
        lines.append(f"- {tool['name']}：{tool['description']}\n  参数：{params}")
    return "\n".join(lines)


def build_tool_selection_system_prompt() -> str:
    """生成「选择工具」这一步的 system 提示词"""
    return f"""你是一个音乐 App 的智能助手，负责把用户的操作类请求映射到可用的工具上。

## 可用工具
{render_tool_catalog()}

## 规则
1. 只有当用户明确要求做上面某个工具对应的事情时，才选择该工具；否则 tool 返回 "none"。
2. 参数从用户这句话里提取；如果用户用「这首歌 / 这些歌 / 刚才的歌」指代上一轮结果，
   请从对话历史里找出对应的歌曲 id 填进 musicIds。
3. 用户可能只知道收藏夹名称和歌曲名称，不需要你查 id，服务端会自动解析。
4. 只输出 JSON，不要输出解释性文字、不要加代码块。

## 输出格式
{{"tool": "工具名或 none", "params": {{...}}, "explanation": "一句话说明"}}

## 示例
用户输入: "帮我创建大陆男歌手收藏夹"
输出: {{"tool": "createFavoriteDirectory", "params": {{"name": "大陆男歌手"}}, "explanation": "创建收藏夹"}}

用户输入: "把周杰伦的歌曲添加到大陆男歌手收藏夹中"
输出: {{"tool": "addMusicToFavorite", "params": {{"favoriteName": "大陆男歌手", "authorName": "周杰伦"}}, "explanation": "把周杰伦的歌加入收藏夹"}}

用户输入: "帮我把大陆男歌手收藏夹删除掉"
输出: {{"tool": "deleteFavoriteDirectory", "params": {{"name": "大陆男歌手"}}, "explanation": "删除收藏夹及其歌曲"}}

用户输入: "帮我把大陆男歌手收藏夹名称改成大陆歌手"
输出: {{"tool": "renameFavoriteDirectory", "params": {{"oldName": "大陆男歌手", "newName": "大陆歌手"}}, "explanation": "重命名收藏夹"}}

用户输入: "帮我把这首歌分享到音乐圈"
输出: {{"tool": "shareMusicToCircle", "params": {{"musicIds": [1791], "content": "分享一首好歌"}}, "explanation": "分享到音乐圈"}}

用户输入: "今天天气怎么样"
输出: {{"tool": "none", "params": {{}}, "explanation": "与音乐无关"}}
"""


# ==================== 参数兼容处理 ====================
def _param(params: Dict[str, Any], *keys: str) -> Optional[Any]:
    """按多个候选 key 取值（大模型可能用不同写法），None/空串视为没给"""
    for key in keys:
        if key in params and params[key] not in (None, "", [], {}):
            return params[key]
    return None


def _music_ids(params: Dict[str, Any]) -> List[int]:
    raw = _param(params, "musicIds", "music_ids", "ids", "id")
    if raw is None:
        return []
    if isinstance(raw, (int, str)):
        raw = [raw]
    result = []
    for item in raw:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


# ==================== 收藏夹 / 歌曲解析 ====================
def _find_directory_id(db: Session, user_id: str, name: str) -> Optional[int]:
    row = db.execute(
        text("SELECT id FROM music_favorite_directory WHERE user_id = :user_id AND name = :name LIMIT 1"),
        {"user_id": user_id, "name": name},
    ).first()
    return int(row[0]) if row else None


def _find_music(db: Session, params: Dict[str, Any], limit: int = MAX_SONGS) -> List[Dict[str, Any]]:
    """按 id 或名称条件找歌曲：优先 musicIds，其次 songName/authorName/albumName 模糊匹配"""
    ids = _music_ids(params)
    if ids:
        placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
        rows = db.execute(
            text(f"SELECT id, song_name AS songName, author_name AS authorName FROM music "
                 f"WHERE id IN ({placeholders}) LIMIT :limit"),
            {**{f"id{i}": v for i, v in enumerate(ids)}, "limit": limit},
        ).mappings().all()
    else:
        song_name = _param(params, "songName", "song_name", "song")
        author_name = _param(params, "authorName", "author_name", "author", "singer")
        album_name = _param(params, "albumName", "album_name", "album")
        if not any([song_name, author_name, album_name]):
            return []
        conditions: List[str] = ["1=1"]
        values: Dict[str, Any] = {"limit": limit}
        if song_name:
            conditions.append("song_name LIKE :song_name")
            values["song_name"] = f"%{song_name}%"
        if author_name:
            conditions.append("author_name LIKE :author_name")
            values["author_name"] = f"%{author_name}%"
        if album_name:
            conditions.append("album_name LIKE :album_name")
            values["album_name"] = f"%{album_name}%"
        rows = db.execute(
            text(f"SELECT id, song_name AS songName, author_name AS authorName FROM music "
                 f"WHERE {' AND '.join(conditions)} LIMIT :limit"),
            values,
        ).mappings().all()
    return [dict(row) for row in rows]


def _describe_songs(songs: List[Dict[str, Any]], max_show: int = 3) -> str:
    shown = "、".join(f"{s.get('authorName') or ''}《{s.get('songName') or ''}》" for s in songs[:max_show])
    return shown + (f" 等 {len(songs)} 首" if len(songs) > max_show else "")


# ==================== 各工具实现 ====================
def create_favorite_directory(db: Session, user_id: str, params: Dict[str, Any]) -> str:
    name = (_param(params, "name", "favoriteName", "favorite_name", "directoryName") or "").strip()
    if not name:
        return "请告诉我要创建的收藏夹名称。"
    if _find_directory_id(db, user_id, name):
        return f"你已经有一个叫「{name}」的收藏夹了，不需要重复创建。"
    db.execute(
        text("INSERT INTO music_favorite_directory(name, user_id, create_time, update_time) "
             "VALUES (:name, :user_id, NOW(), NOW())"),
        {"name": name, "user_id": user_id},
    )
    db.commit()
    logger.info(f"[AgentTool] 创建收藏夹成功: user_id={user_id}, name={name}")
    return f"已为你创建收藏夹「{name}」。"


def delete_favorite_directory(db: Session, user_id: str, params: Dict[str, Any]) -> str:
    name = (_param(params, "name", "favoriteName", "favorite_name", "directoryName") or "").strip()
    if not name:
        return "请告诉我要删除的收藏夹名称。"
    favorite_id = _find_directory_id(db, user_id, name)
    if not favorite_id:
        return f"没有找到名为「{name}」的收藏夹。"
    row = db.execute(
        text("SELECT COUNT(*) FROM music_favorite_list WHERE favorite_id = :favorite_id"),
        {"favorite_id": favorite_id},
    ).scalar()
    db.execute(
        text("DELETE FROM music_favorite_directory WHERE id = :favorite_id AND user_id = :user_id"),
        {"favorite_id": favorite_id, "user_id": user_id},
    )
    db.commit()
    logger.info(f"[AgentTool] 删除收藏夹成功: user_id={user_id}, name={name}, 关联歌曲={row}")
    return f"已删除收藏夹「{name}」，连同其中的 {row or 0} 首歌曲。"


def rename_favorite_directory(db: Session, user_id: str, params: Dict[str, Any]) -> str:
    old_name = (_param(params, "oldName", "old_name", "name", "favoriteName") or "").strip()
    new_name = (_param(params, "newName", "new_name", "toName", "targetName") or "").strip()
    if not old_name or not new_name:
        return "请告诉我原收藏夹名称和要改成的新名称。"
    favorite_id = _find_directory_id(db, user_id, old_name)
    if not favorite_id:
        return f"没有找到名为「{old_name}」的收藏夹。"
    if _find_directory_id(db, user_id, new_name):
        return f"你已经有一个叫「{new_name}」的收藏夹了，换一个名称吧。"
    db.execute(
        text("UPDATE music_favorite_directory SET name = :new_name, update_time = NOW() "
             "WHERE id = :favorite_id AND user_id = :user_id"),
        {"new_name": new_name, "favorite_id": favorite_id, "user_id": user_id},
    )
    db.commit()
    logger.info(f"[AgentTool] 重命名收藏夹成功: user_id={user_id}, {old_name} -> {new_name}")
    return f"已把收藏夹「{old_name}」重命名为「{new_name}」。"


def add_music_to_favorite(db: Session, user_id: str, params: Dict[str, Any]) -> str:
    favorite_name = (_param(params, "favoriteName", "favorite_name", "directoryName", "name") or "").strip()
    if not favorite_name:
        return "请告诉我要添加到哪个收藏夹。"
    favorite_id = _find_directory_id(db, user_id, favorite_name)
    if not favorite_id:
        return f"没有找到名为「{favorite_name}」的收藏夹，你可以先让我创建它。"

    songs = _find_music(db, params)
    if not songs:
        return f"没有找到符合条件「{favorite_name}」要收藏的歌曲，请告诉我歌曲名或歌手名。"

    added = 0
    for song in songs:
        # 已在该收藏夹里就跳过（music_favorite_list 无唯一约束，这里显式判重）
        exists = db.execute(
            text("SELECT COUNT(*) FROM music_favorite_list WHERE favorite_id = :favorite_id AND music_id = :music_id"),
            {"favorite_id": favorite_id, "music_id": song["id"]},
        ).scalar()
        if exists:
            continue
        db.execute(
            text("INSERT INTO music_favorite_list(music_id, favorite_id, create_time, update_time) "
                 "VALUES (:music_id, :favorite_id, NOW(), NOW())"),
            {"music_id": song["id"], "favorite_id": favorite_id},
        )
        added += 1
    db.commit()
    logger.info(f"[AgentTool] 添加收藏成功: user_id={user_id}, favorite={favorite_name}, 新增={added}/{len(songs)}")
    if added == 0:
        return f"这些歌曲都已经在收藏夹「{favorite_name}」里了。"
    return f"已把 {_describe_songs(songs)} 添加到收藏夹「{favorite_name}」（新增 {added} 首）。"


def share_music_to_circle(db: Session, user_id: str, params: Dict[str, Any]) -> str:
    """发音乐圈：写入 circle 表（type='MUSIC'，relation_id = music.id），与 circle 模块 insertCircle 一致"""
    songs = _find_music(db, params, limit=3)
    if not songs:
        return "请告诉我要分享到音乐圈的歌曲（可以说歌名、歌手，或直接说“这首歌”）。"

    song = songs[0]
    content = (_param(params, "content", "text", "message") or "").strip()
    if not content:
        content = f"分享歌曲：{song.get('authorName') or ''} - 《{song.get('songName') or ''}》"
    try:
        permission = int(_param(params, "permission") or 1)
    except (TypeError, ValueError):
        permission = 1

    db.execute(
        text("INSERT INTO circle(content, imgs, relation_id, type, user_id, permission, create_time, update_time) "
             "VALUES (:content, NULL, :relation_id, 'MUSIC', :user_id, :permission, NOW(), NOW())"),
        {"content": content, "relation_id": song["id"], "user_id": user_id, "permission": permission},
    )
    db.commit()
    logger.info(f"[AgentTool] 分享音乐圈成功: user_id={user_id}, music_id={song['id']}, content={content}")
    return f"已把《{song.get('songName') or ''}》分享到音乐圈啦：{content}"


TOOL_HANDLERS = {
    "addMusicToFavorite": add_music_to_favorite,
    "createFavoriteDirectory": create_favorite_directory,
    "deleteFavoriteDirectory": delete_favorite_directory,
    "renameFavoriteDirectory": rename_favorite_directory,
    "shareMusicToCircle": share_music_to_circle,
}


def parse_tool_selection(raw: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """解析大模型返回的工具选择 JSON（容忍 ```json 包裹、多余文字、大小写差异）。

    返回 (工具名, 参数字典)；没选中工具（none / 解析失败 / 工具名不认识）时返回 (None, {})，
    调用方据此输出「只能回答与音乐相关的问题」的统一提示。
    """
    if not raw:
        return None, {}
    value = raw.strip()
    if value.startswith("```"):
        value = value.strip("`").strip()
        if value.lower().startswith("json"):
            value = value[4:].strip()
    start, end = value.find("{"), value.rfind("}")
    if start == -1 or end == -1:
        return None, {}
    try:
        data = json.loads(value[start:end + 1])
    except Exception:
        logger.warning(f"[AgentTool] 工具选择结果不是合法 JSON: {raw[:120]}")
        return None, {}
    if not isinstance(data, dict):
        return None, {}

    tool = str(data.get("tool") or data.get("name") or "").strip()
    if not tool or tool.lower() in ("none", "null", "no", "无", "没有"):
        return None, {}
    if tool not in TOOL_HANDLERS:
        normalized = tool.lower().replace("_", "")
        for name in TOOL_NAMES:
            if name.lower() == tool.lower() or name.lower().replace("_", "") == normalized:
                tool = name
                break
        else:
            logger.warning(f"[AgentTool] 模型选了不存在的工具: {tool}")
            return None, {}

    params = data.get("params") or data.get("arguments") or {}
    if not isinstance(params, dict):
        params = {}
    return tool, params


def execute_tool(db: Session, user_id: str, tool_name: str, params: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """执行工具并返回给用户的话术；工具名不认识时返回 None（调用方据此走统一提示）"""
    handler = TOOL_HANDLERS.get((tool_name or "").strip())
    if not handler:
        return None
    try:
        return handler(db, user_id, params or {})
    except Exception as e:
        logger.error(f"[AgentTool] 工具执行失败: tool={tool_name}, err={str(e)}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return f"抱歉，操作没有成功：{str(e)}"
