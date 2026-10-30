import os, tempfile, requests
from pathlib import Path
import gradio as gr
import PyPDF2

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
except:
    client = None
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except:
    TTS_AVAILABLE = False

# ========= CONFIG =========
PAYSTACK_PUBLIC_KEY = "pk_test_xxxxxxxxxxxxxxxx" # CHANGE THIS TO YOUR PAYSTACK KEY
PAID_USERS_5 = set()  # Users who paid GH₵5
PAID_USERS_10 = set() # Users who paid GH₵10

# ========= PAYMENT HELPERS =========
def check_paid(email, amount):
    if amount == 5:
        return email in PAID_USERS_5 or email in PAID_USERS_10 # GH₵10 includes GH₵5 features
    if amount == 10:
        return email in PAID_USERS_10
    return False

def add_paid_user(email, amount):
    if amount == 5:
        PAID_USERS_5.add(email)
    else:
        PAID_USERS_10.add(email)
    return f"✅ Payment confirmed for {email} - GH₵{amount} unlocked!"

# ========= CORE AI FUNCTIONS =========
def transcribe_audio(audio_path):
    if not audio_path or not client: return ""
    try:
        with open(audio_path, "rb") as f:
            t = client.audio.transcriptions.create(model="whisper-1", file=f)
            return t.text
    except:
        return ""

def text_to_speech(text):
    if not TTS_AVAILABLE or not text: return None
    try:
        tts = gTTS(text=text[:500], lang='en')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return tmp.name
    except:
        return None

def detect_intent(message):
    msg = message.lower()
    if "logo video" in msg or "video logo" in msg or "logo ad video" in msg:
        return "logo_video" # GH₵10
    if "business video" in msg or "video ad" in msg or "advertisement video" in msg or "promo video" in msg:
        return "business_video" # GH₵10
    if "logo" in msg:
        return "logo" # GH₵5
    if "business presentation" in msg or "pitch deck" in msg or "business plan" in msg or "presentation" in msg:
        return "presentation" # GH₵5
    return "free_chat"

def chat_function(message, history, files, audio_input, user_email):
    if audio_input:
        tr = transcribe_audio(audio_input)
        message = f"{message} {tr}".strip() if message else tr
    if not message and not files:
        return history, "", None, "", False, False

    file_context = ""
    if files:
        for fp in files:
            if Path(fp).suffix.lower() == ".pdf":
                try:
                    with open(fp, "rb") as f:
                        r = PyPDF2.PdfReader(f)
                        file_context += "".join([p.extract_text() for p in r.pages[:3]])[:3000]
                except: pass

    intent = detect_intent(message)
    
    # --- PAYWALL POPUP LOGIC ---
    show_pay5 = False
    show_pay10 = False
    pay_message = ""

    if intent in ["logo", "presentation"]:
        if not check_paid(user_email, 5):
            show_pay5 = True
            pay_message = f"🔒 **PREMIUM FEATURE (GH₵5)**\nYou asked for: **{intent}**\n\nPlease pay GH₵5 to unlock Logo & Business Presentation generator.\nClick the green Pay button below."
            history.append((message, pay_message))
            return history, "", None, pay_message, True, False

    if intent in ["logo_video", "business_video"]:
        if not check_paid(user_email, 10):
            show_pay10 = True
            pay_message = f"🔒 **PREMIUM VIDEO (GH₵10)**\nYou asked for: **{intent}**\n\nPlease pay GH₵10 to unlock Business & Logo Video Advertisement generator."
            history.append((message, pay_message))
            return history, "", None, pay_message, False, True

    # --- FREE CHAT ---
    full_prompt = f"{file_context}\nUser wants {intent}: {message}"
    if client:
        msgs = [{"role":"system","content":"You are Exquisite AI by ExquisiteTechGH. Helpful, concise."}]
        for h in history[-6:]: 
            msgs.append({"role":"user","content":h[0]}); msgs.append({"role":"assistant","content":h[1]})
        msgs.append({"role":"user","content":full_prompt})
        ans = client.chat.completions.create(model="gpt-4o-mini", messages=msgs).choices[0].message.content
    else:
        ans = f"✅ Exquisite AI (Free Mode): I understood you want {intent}. Result for: {message}"

    history.append((message, ans))
    voice = text_to_speech(ans)
    return history, "", voice, "", False, False

def generate_free_image(prompt):
    """This is FREE image generation - no paywall"""
    if not prompt.strip(): return None, "Enter prompt"
    enhanced = f"photorealistic, 8k, cinematic, {prompt}"
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(enhanced)}?width=1024&height=1024&nologo=true&enhance=true"
        data = requests.get(url, timeout=40).content
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(data); tmp.close()
        return tmp.name, f"✅ Free Image: {prompt}"
    except Exception as e:
        return None, str(e)

def generate_premium_logo(prompt, user_email):
    if not check_paid(user_email, 5):
        return None, "🔒 Pay GH₵5 first in Premium tab"
    enhanced = f"professional logo design, vector, minimalist, clean, {prompt}, white background, 8k"
    return generate_free_image(enhanced)

def generate_premium_video_ad(prompt, user_email):
    if not check_paid(user_email, 10):
        return None, "🔒 Pay GH₵10 first in Premium tab"
    # For now: generate storyboard image + script. Later connect to real video API like Pika/Runway
    script = f"VIDEO AD SCRIPT for: {prompt}\nScene 1: Hook (0-3s)\nScene 2: Product Show (3-7s)\nScene 3: Call to Action (7-10s)\nVoiceover: 'Get {prompt} today!'"
    img, _ = generate_free_image(f"business advertisement poster for {prompt}")
    return img, script

# ========= UI =========
with gr.Blocks(theme=gr.themes.Soft(primary_hue="green", secondary_hue="yellow"), title="Exquisite AI") as demo:
    gr.Markdown("# 🇬🇭 Exquisite AI v3 - Monetized")
    gr.Markdown("Free Chat & Images | **GH₵5 = Logo & Presentation** | **GH₵10 = Video Ads**")

    user_email_state = gr.Textbox(label="Your Email / MoMo (for unlocking)", placeholder="you@gmail.com or 055XXXXXXX", value="guest@exquisite.ai")

    with gr.Tab("💬 Chat (with Paywall Detection)"):
        chatbot = gr.Chatbot(height=400)
        with gr.Row():
            msg = gr.Textbox(placeholder="Try: 'create a logo for my shop' or 'make business presentation'", scale=4)
            send = gr.Button("Send 🚀", variant="primary")
        with gr.Row():
            audio_in = gr.Audio(sources=["microphone"], type="filepath", label="🎤 Speak")
            audio_out = gr.Audio(label="🔊 AI Reply", autoplay=True)
        file_upload = gr.File(file_count="multiple", label="📎 Attach")
        
        paywall_msg = gr.Textbox(label="System", visible=False)
        show_pay5_box = gr.State(False)
        show_pay10_box = gr.State(False)

        msg.submit(chat_function, [msg, chatbot, file_upload, audio_in, user_email_state], [chatbot, msg, audio_out, paywall_msg, show_pay5_box, show_pay10_box])
        send.click(chat_function, [msg, chatbot, file_upload, audio_in, user_email_state], [chatbot, msg, audio_out, paywall_msg, show_pay5_box, show_pay10_box])

    with gr.Tab("🎨 Free Image Generation"):
        gr.Markdown("This is FREE - no payment needed")
        free_prompt = gr.Textbox(label="Image Prompt")
        free_btn = gr.Button("Generate FREE Image ✨")
        free_img = gr.Image(label="Result")
        free_status = gr.Textbox(label="Status")
        free_btn.click(generate_free_image, free_prompt, [free_img, free_status])

    with gr.Tab("💰 Premium - GH₵5 & GH₵10"):
        gr.Markdown("### Pay to unlock premium generators")
        
        # PAYSTACK BUTTONS
        pay_html = f"""
        <div style="display:flex;gap:15px;flex-direction:column;">
            <button onclick="pay(500)" style="background:#00a859;color:white;padding:18px;border-radius:12px;font-size:18px;font-weight:bold;border:none;">💚 Pay GH₵5 - Unlock LOGO & PRESENTATION</button>
            <button onclick="pay(1000)" style="background:#000;color:white;padding:18px;border-radius:12px;font-size:18px;font-weight:bold;border:none;">🖤 Pay GH₵10 - Unlock VIDEO ADS (Logo + Business)</button>
        </div>
        <p id="pay-status" style="margin-top:15px;font-weight:bold;"></p>
        <script src="https://js.paystack.co/v1/inline.js"></script>
        <script>
        function pay(kobo){{
            var email = document.querySelectorAll('input')[0].value || 'guest@exquisite.ai';
            if(!email.includes('@')) email = email + '@momo.com';
            var handler = PaystackPop.setup({{
                key: '{PAYSTACK_PUBLIC_KEY}',
                email: email,
                amount: kobo,
                currency: 'GHS',
                callback: function(res){{
                    document.getElementById('pay-status').innerText = '✅ Payment success! Ref: ' + res.reference + '. Go back to Chat, your premium is unlocked for ' + email;
                }},
                onClose: function(){{ document.getElementById('pay-status').innerText = 'Payment cancelled'; }}
            }});
            handler.openIframe();
        }}
        </script>
        """
        gr.HTML(pay_html)
        
        gr.Markdown("---")
        with gr.Row():
            with gr.Column():
                gr.Markdown("#### GH₵5 - Logo Generator")
                logo_prompt = gr.Textbox(label="Logo idea")
                logo_btn = gr.Button("Generate Premium Logo (GH₵5)")
                logo_img = gr.Image(label="Logo")
                logo_stat = gr.Textbox(label="Status")
                logo_btn.click(generate_premium_logo, [logo_prompt, user_email_state], [logo_img, logo_stat])
            with gr.Column():
                gr.Markdown("#### GH₵10 - Video Ad Generator")
                video_prompt = gr.Textbox(label="Business / Product for Video Ad")
                video_btn = gr.Button("Generate Video Ad (GH₵10)")
                video_img = gr.Image(label="Storyboard")
                video_stat = gr.Textbox(label="Script")
                video_btn.click(generate_premium_video_ad, [video_prompt, user_email_state], [video_img, video_stat])

        # Admin unlock (for you to test without paying)
        gr.Markdown("---\n**For YOU (Owner) - Test Unlock:**")
        with gr.Row():
            admin_email = gr.Textbox(label="Email to unlock")
            admin_amt = gr.Radio([5,10], label="Amount", value=5)
            admin_btn = gr.Button("Unlock for Free (Admin)")
            admin_stat = gr.Textbox(label="Result")
            admin_btn.click(add_paid_user, [admin_email, admin_amt], admin_stat)

    gr.Markdown("Built with ❤️ by ExquisiteTechGH | Not affiliated with Meta")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
