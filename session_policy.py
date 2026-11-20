"""Conservative explicit exit phrases; ordinary sentences mentioning goodbye stay active."""
import re

def is_goodbye(text):
    compact=re.sub(r'[\s，。！？、,.!?：:~～]+','',str(text))
    return re.fullmatch(r'(?:好的?|嗯|豆包|谢谢)?(?:再见|拜拜|结束对话|退出对话|不聊了|先这样吧|别说了|停一下|闭嘴)(?:豆包|了|吧)?',compact) is not None
