import unittest
from screen_text import ScreenText

class ScreenTextTests(unittest.TestCase):
    def question(self,screen,text,item=None):
        screen.event({'type':'conversation.item.input_audio_transcription.started','item_id':item})
        screen.event({'type':'conversation.item.input_audio_transcription.completed','text':text,'item_id':item})

    def test_new_question_clears_answer_without_response_created(self):
        screen=ScreenText();self.question(screen,'第一问','q1')
        screen.event({'type':'response.output_text.delta','delta':'第一答','response_id':'r1'})
        screen.complete()
        self.question(screen,'第二问','q2')
        self.assertEqual(screen.assistant,'')
        screen.event({'type':'response.output_text.delta','delta':'第二答','response_id':'r2'})
        value=screen.snapshot('speaking')
        self.assertEqual(value['current']['assistant'],'第二答')
        self.assertEqual(value['previous']['user'],'第一问')
        self.assertEqual(value['previous']['assistant'],'第一答')

    def test_duplicate_response_created_does_not_erase_reply(self):
        screen=ScreenText();self.question(screen,'问题')
        screen.event({'type':'response.output_text.delta','delta':'正在回答','response_id':'r1'})
        screen.event({'type':'response.created','response':{'id':'r1'}})
        self.assertEqual(screen.assistant,'正在回答')

    def test_cumulative_reply_replaces_but_incremental_reply_still_appends(self):
        screen=ScreenText();self.question(screen,'问题')
        for piece in ('我','我会','我会回答','我会回答'):
            screen.event({'type':'response.output_text.delta','delta':piece})
            self.assertEqual(screen.assistant,piece)
        screen.event({'type':'response.output_text.delta','delta':'我来回答'})
        self.assertEqual(screen.assistant,'我来回答')
        self.question(screen,'再来')
        for piece in ('哈','哈','，好的'):
            screen.event({'type':'response.output_text.delta','delta':piece})
        self.assertEqual(screen.assistant,'哈哈，好的')

    def test_interrupt_freezes_previous_and_rejects_old_turn_events(self):
        screen=ScreenText();self.question(screen,'旧问题','q1')
        screen.event({'type':'response.output_text.delta','delta':'已经收到的一段','response_id':'old'})
        self.assertTrue(screen.interrupt());self.assertFalse(screen.interrupt())
        frozen=screen.snapshot('interrupting')['previous']
        self.assertEqual(frozen['status'],'interrupted')
        self.assertEqual(frozen['assistant'],'已经收到的一段')
        self.assertFalse(screen.event({'type':'response.output_text.done','text':'迟到的旧结尾','response_id':'old'}))
        self.question(screen,'新问题','q2')
        self.assertFalse(screen.event({'type':'response.output_text.delta','delta':'旧片段','response_id':'old'}))
        self.assertFalse(screen.event({'type':'conversation.item.input_audio_transcription.completed','text':'旧识别','item_id':'q1'}))
        screen.event({'type':'response.output_text.delta','delta':'新的回答','response_id':'new'})
        self.assertEqual(screen.assistant,'新的回答')
        self.assertEqual(screen.snapshot('speaking')['previous'],frozen)

    def test_only_two_turns_and_short_previous_summary_are_retained(self):
        screen=ScreenText()
        for index in range(3):
            self.question(screen,'问题'+str(index)+'问'*200,'q'+str(index))
            screen.event({'type':'response.output_text.done','text':'答'*3000+'结论'+str(index),'response_id':'r'+str(index)})
        snapshot=screen.snapshot('listening')
        self.assertTrue(snapshot['previous']['user'].startswith('问题1'))
        self.assertTrue(snapshot['previous']['assistant'].endswith('结论1'))
        self.assertLessEqual(len(snapshot['previous']['user']),101)
        self.assertLessEqual(len(snapshot['previous']['assistant']),181)
        self.assertNotIn('history',snapshot)
        import json
        self.assertLess(len(json.dumps(snapshot,ensure_ascii=False)),24000)

    def test_final_text_and_repeated_event_cannot_be_appended_again(self):
        screen=ScreenText();self.question(screen,'问题')
        event={'type':'response.output_text.delta','delta':'你好','event_id':'same'}
        screen.event(event);self.assertFalse(screen.event(event))
        screen.event({'type':'response.output_text.done','text':'你好。'})
        self.assertFalse(screen.event({'type':'response.output_text.delta','delta':'你好。'}))
        self.assertEqual(screen.assistant,'你好。')

    def test_asr_partial_hypotheses_replace_instead_of_accumulating(self):
        screen=ScreenText()
        for partial in ('今','今天','今天天','今天天气','今天天气好','今天天气好'):
            screen.event({'type':'conversation.item.input_audio_transcription.delta','delta':partial})
            self.assertEqual(screen.snapshot('listening')['user'],partial)
        # Recognition may revise or shorten a hypothesis before finalizing it.
        for partial in ('今天的天气好','今天天气','今天天气很好。'):
            screen.event({'type':'conversation.item.input_audio_transcription.delta','delta':partial})
            self.assertEqual(screen.user,partial)

    def test_streamed_text_final_correction_and_new_turn(self):
        screen=ScreenText()
        for event in [
            {'type':'conversation.item.input_audio_transcription.started'},
            {'type':'conversation.item.input_audio_transcription.delta','delta':'今天天'},
            {'type':'conversation.item.input_audio_transcription.delta','delta':'今天天气'},
            {'type':'conversation.item.input_audio_transcription.completed','text':'今天天气怎么样？'},
            {'type':'response.created'},
            {'type':'response.output_text.delta','delta':'请问'},
            {'type':'response.output_text.delta','delta':'在哪个城市？'},
        ]:screen.event(event)
        self.assertEqual(screen.user,'今天天气怎么样？')
        self.assertEqual(screen.assistant,'请问在哪个城市？')
        screen.event({'type':'response.output_text.done','text':'你想查询哪个城市的天气？'})
        self.assertEqual(screen.assistant,'你想查询哪个城市的天气？')
        screen.event({'type':'conversation.item.input_audio_transcription.started'})
        screen.event({'type':'conversation.item.input_audio_transcription.completed','transcript':'上海'})
        screen.event({'type':'response.created'})
        self.assertEqual(screen.user,'上海');self.assertEqual(screen.assistant,'')

    def test_payloads_remain_bounded_and_audio_does_not_become_text(self):
        screen=ScreenText();before=screen.snapshot('listening')
        self.assertFalse(screen.event({'type':'response.output_audio.delta','delta':'SECRET_AUDIO'}))
        self.assertEqual(screen.snapshot('listening'),before)
        screen.event({'type':'conversation.item.input_audio_transcription.delta','delta':'字'*10000})
        screen.event({'type':'response.output_text.done','text':'答'*10000})
        self.assertEqual(len(screen.user),1200);self.assertEqual(len(screen.assistant),4000)

if __name__=='__main__':unittest.main()
