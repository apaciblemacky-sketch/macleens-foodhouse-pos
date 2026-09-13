#!/usr/bin/env python3
"""Static checks for Digital 24-hour trials + protected Gemini bridge."""
from pathlib import Path
import py_compile
from jinja2 import Environment, TemplateSyntaxError

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / 'templates'
source = (ROOT / 'app.py').read_text(encoding='utf-8')

def need(text, marker, label):
    if marker not in text:
        raise AssertionError(f'{label}: missing {marker!r}')

for marker in [
    'digital-accounts-chatlite-v41.1',
    'class DigitalAppTrial(db.Model):',
    'class DigitalHostedAIUsage(db.Model):',
    "trial_hours = db.Column(db.Integer, default=24",
    "hosted_gemini_enabled = db.Column(db.Boolean, default=False",
    "@app.route('/digital/item/<int:item_id>/trial/start', methods=['POST'])",
    "@app.route('/digital/apps/trial/<string:access_token>')",
    "@app.route('/digital/apps/chat-lite/trial/<string:access_token>')",
    "@app.route('/api/digital/hosted-gemini', methods=['POST'])",
    "GEMINI_API_KEY",
    "window.MacleensAI",
    "digital_hosted_ai_usage_allow",
]:
    need(source, marker, 'app.py')

item = (T / 'digital' / 'item.html').read_text(encoding='utf-8')
for marker in ['Start Free Trial', 'Resume Free Trial', 'Gemini API key stays on the server', 'AI prompts are relayed to Google Gemini']:
    need(item, marker, 'Digital item page')

index = (T / 'digital' / 'index.html').read_text(encoding='utf-8')
need(index, 'Free Trial', 'Digital catalog')

admin = (T / 'digital' / 'admin.html').read_text(encoding='utf-8')
for marker in ['Free Trial', 'trial_hours', 'Macleen’s Gemini Bridge', 'hosted_gemini_trial_limit', 'hosted_gemini_paid_daily_limit', 'window.MacleensAI.generate']:
    need(admin, marker, 'Digital Admin')

viewer = (T / 'digital' / 'apps' / 'hosted_app_viewer.html').read_text(encoding='utf-8')
for marker in ['mfh-gemini-request', '/api/digital/hosted-gemini', 'mfh-host-storage-hello', "access_mode=='TRIAL'"]:
    need(viewer, marker, 'Hosted app viewer')
if 'GEMINI_API_KEY' in viewer or 'GOOGLE_API_KEY' in viewer:
    raise AssertionError('Hosted app viewer must never contain Gemini secret environment variable code.')

chat = (T / 'digital' / 'apps' / 'chat_lite.html').read_text(encoding='utf-8')
need(chat, "access_mode == 'TRIAL'", 'CHAT Lite')

py_compile.compile(str(ROOT / 'app.py'), doraise=True)
env = Environment()
for template in sorted(T.rglob('*.html')):
    try:
        env.parse(template.read_text(encoding='utf-8'))
    except TemplateSyntaxError as exc:
        raise AssertionError(f'Jinja syntax error in {template.relative_to(ROOT)}:{exc.lineno}: {exc.message}') from exc

print('V40 DIGITAL TRIAL + GEMINI BRIDGE SMOKE CHECK PASSED')
