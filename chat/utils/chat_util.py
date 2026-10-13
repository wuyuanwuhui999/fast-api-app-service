# 文档问答：上下文里每一段摘录都会带「创建时间」，模型必须靠 system prompt 里的规则才知道该信哪一份文档
# （同一份文档的所有分片共用同一个 create_time；这里的规则文本与 Spring 项目 chat/constants/SystemtConstants.java 保持一致）
DOC_TIME_RULE = """【文档时间优先规则】
下面提供的文档摘录，每一段都标注了「创建时间」（该文档入库的时间，越晚越新）。
1. 当不同文档对同一问题给出不一致的说法时，必须以「创建时间」最新的那段文档为准，只采用最新文档的结论，忽略时间较早的旧文档内容；
2. 如果某段摘录的创建时间显示为「未知」，说明它没有时间信息，视为最旧的文档，只有在没有其它带时间的文档时才参考它；
3. 需要在回答中说明你依据的是哪一份文档（例如「根据最新的《合同v2.pdf》」），但不要把新旧文档互相矛盾的内容混在一起下结论；
4. 如果最新文档完全没有提到该问题，再依次参考更早的文档，并明确说明参考的是较早版本。"""


# 会话记录压缩阈值：MongoDB 里的原始会话消息超过这个条数，就用当前模型压缩成概要
CHAT_HISTORY_SUMMARY_THRESHOLD = 5

# 会话概要注入 system prompt 时的标题（与 Spring SystemtConstants.HISTORY_SUMMARY_TITLE 一致）
HISTORY_SUMMARY_TITLE = "【历史会话概要（更早的对话内容，已压缩）】"

# 会话记录压缩提示词（与 Spring SystemtConstants.CHAT_SUMMARY_PROMPT 保持一致）
CHAT_SUMMARY_PROMPT = """你是会话记忆压缩助手。请把下面的会话记录压缩成一段简洁的概要总结，用于后续对话的上下文：
1. 保留：用户的目标与偏好、已确认的事实与结论、待办或未完成事项、关键标识信息（人名、编号、参数等）；
2. 去掉：寒暄、重复内容、与用户目标无关的闲聊；
3. 如果给了「已有概要」，请把新增会话记录合并进去，输出合并后的完整概要，不要丢掉已有概要里的关键信息；
4. 只输出概要正文，不要输出「概要：」之类的前缀，也不要任何解释。"""


class PromptUtil:
    @staticmethod
    def get_file_extension(filename: str) -> str:
        if not filename:
            return ""

        dot_index = filename.rfind(".")
        if dot_index == -1 or dot_index == len(filename) - 1:
            return ""

        return filename[dot_index + 1:]
