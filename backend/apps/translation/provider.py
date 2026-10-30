"""Google Cloud Translation (text translation), NOT Google Text-to-Speech.
Requires Google Cloud project/billing + Application Default Credentials.
"""
import html


def translate_fr_mg(text):
    if not text.strip():return ''
    from google.cloud import translate_v2 as translate
    client=translate.Client()
    # Split long fields into modest pieces. Keep paragraphs and whitespace in order.
    parts=[];remaining=text
    while len(remaining)>3500:
        cut=remaining.rfind('\n',0,3500)
        if cut < 1400:cut=remaining.rfind(' ',0,3500)
        if cut < 1400:cut=3500
        parts.append(remaining[:cut]);remaining=remaining[cut:]
    if remaining:parts.append(remaining)
    translated=[]
    for part in parts:
        result=client.translate(part,target_language='mg',source_language='fr',format_='text')
        translated.append(html.unescape(result['translatedText']))
    return ''.join(translated)
