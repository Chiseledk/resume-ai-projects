from http import HTTPStatus
from dashscope.audio.asr import Recognition
import dashscope
import sys
sys.path.insert(0, '.')
from config import DASHSCOPE_API_KEY

dashscope.api_key = DASHSCOPE_API_KEY

print("=" * 50)
print("ASR API 测试")
print("=" * 50)

recognition = Recognition(
    model='paraformer-realtime-v2',
    format='wav',
    sample_rate=16000,
    language_hints=['zh', 'en'],
    callback=None
)

result = recognition.call('test.wav')

if result.status_code == HTTPStatus.OK:
    print('✅ 识别结果:')
    print(result.get_sentence())
else:
    print('❌ 错误信息:', result.message)

print(
    '[调试信息] requestId: {}, 首包延迟: {}ms, 尾包延迟: {}ms'
    .format(
        recognition.get_last_request_id(),
        recognition.get_first_package_delay(),
        recognition.get_last_package_delay(),
    )
)