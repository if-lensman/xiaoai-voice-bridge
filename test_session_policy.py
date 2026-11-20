import unittest
from session_policy import is_goodbye

class ExitTests(unittest.TestCase):
    def test_explicit_exit_phrases(self):
        for text in ('再见。','豆包，再见！','好的，拜拜','结束对话','不聊了','再见豆包'):
            with self.subTest(text=text): self.assertTrue(is_goodbye(text))
    def test_mentions_and_empty_recognition_do_not_exit(self):
        for text in ('介绍一下《再见》这首歌','先不要结束对话','为什么要说再见','', '再见是什么意思'):
            with self.subTest(text=text): self.assertFalse(is_goodbye(text))

if __name__=='__main__':unittest.main()
