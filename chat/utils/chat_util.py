# 文档问答：上下文里每一段摘录都会带「创建时间」，模型必须靠 system prompt 里的规则才知道该信哪一份文档
# （同一份文档的所有分片共用同一个 create_time；这里的规则文本与 Spring 项目 chat/constants/SystemtConstants.java 保持一致）
DOC_TIME_RULE = """【文档时间优先规则】
下面提供的文档摘录，每一段都标注了「创建时间」（该文档入库的时间，越晚越新）。
1. 当不同文档对同一问题给出不一致的说法时，必须以「创建时间」最新的那段文档为准，只采用最新文档的结论，忽略时间较早的旧文档内容；
2. 如果某段摘录的创建时间显示为「未知」，说明它没有时间信息，视为最旧的文档，只有在没有其它带时间的文档时才参考它；
3. 需要在回答中说明你依据的是哪一份文档（例如「根据最新的《合同v2.pdf》」），但不要把新旧文档互相矛盾的内容混在一起下结论；
4. 如果最新文档完全没有提到该问题，再依次参考更早的文档，并明确说明参考的是较早版本。"""


class PromptUtil:
    @staticmethod
    def get_file_extension(filename: str) -> str:
        if not filename:
            return ""

        dot_index = filename.rfind(".")
        if dot_index == -1 or dot_index == len(filename) - 1:
            return ""

        return filename[dot_index + 1:]
