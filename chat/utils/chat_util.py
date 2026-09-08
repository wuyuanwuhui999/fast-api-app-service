class PromptUtil:
    @staticmethod
    def get_file_extension(filename: str) -> str:
        if not filename:
            return ""

        dot_index = filename.rfind(".")
        if dot_index == -1 or dot_index == len(filename) - 1:
            return ""

        return filename[dot_index + 1:]
