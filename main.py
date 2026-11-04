import os
import gradio as gr
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import requests
from gtts import gTTS
import tempfile

# --- GROQ FREE CLIENT ---
# Put GROQ_API_KEY in HF Secrets
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.3-70b-versatile"
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "pk_test_xxxx")
CREATOR = "raphaeldorgbefu01-dev"

def ask_ai(prompt):
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Error: {e} - Check your GROQ_API_KEY in Secrets"

def check_paywall(text):
    text = text.lower()
    if "logo" in text:
        return True, "GH₵5", "Logo Design - Pay GH₵5 to continue"
    if "business presentation" in text or "presentation" in text:
        return True, "GH₵5", "Business Presentation - Pay GH₵5 to continue"
    if "video ad" in text or "business video" in text or "advert" in text:
        return True, "GH₵10", "Business Video Ad - Pay GH₵10 to continue"
    return False, "", ""

# --- TABS ---

def free_image_tab(prompt):
    # FREE - No paywall
    if not prompt:
        return "Type something to generate", None
    # Simple image placeholder with text
    img = Image.new("RGB", (512, 512), color=(30, 30, 60))
    d = ImageDraw.Draw(img)
    d.text((20, 240), prompt[:40], fill=(255, 255, 255))
    return f"Free Image for: {prompt} | by {CREATOR}", img

def logo_tab(prompt):
    need_pay, price, msg = check_paywall("logo " + prompt)
    # Show paywall UI
    pay_html = f"""
    <div style="padding:20px; background:#fff3cd; border-radius:10px; text-align:center">
    <h3>{msg}</h3>
    <p>Pay with Paystack MoMo / Card</p>
    <p>Amount: {price}</p>
    <p>After payment, click Generate again</p>
    </div>
    """
    ai_idea = ask_ai(f"Give a logo idea for: {prompt}. Colors, font, symbol.")
    return pay_html, ai_idea

def presentation_tab(topic):
    need_pay, price, msg = check_paywall("business presentation " + topic)
    pay_html = f"""
    <div style="padding:20px; background:#d1ecf1; border-radius:10px; text-align:center">
    <h3>{msg}</h3>
    <p>Pay {price} with MoMo via Paystack</p>
    </div>
    """
    content = ask_ai(f"Create a 5-slide business presentation outline for: {topic}. Slide titles + bullet points.")
    return pay_html, content

def video_tab(script):
    need_pay, price, msg = check_paywall("video ad " + script)
    pay_html = f"""
    <div style="padding:20px; background:#f8d7da; border-radius:10px; text-align:center">
    <h3>{msg}</h3>
    <p>Pay {price} with MoMo via Paystack</p>
    </div>
    """
    ad_script = ask_ai(f"Write a 30-second business video ad script for: {script}. Hook, benefits, call to action.")
    # Make voice
    try:
        tts = gTTS(text=ad_script[:500], lang='en')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        audio = tmp.name
    except:
        audio = None
    return pay_html, ad_script, audio

# --- UI ---
with gr.Blocks(title="Exquisite AI") as demo:
    gr.Markdown("# ✨ Exquisite AI by raphaeldorgbefu01-dev\nFree Images | GH₵5 Logo & Presentation | GH₵10 Video Ad")
    
    with gr.Tab("🖼️ Free Image"):
        inp1 = gr.Textbox(label="Describe your image")
        out1 = gr.Textbox(label="Result")
        img1 = gr.Image(label="Your Image")
        btn1 = gr.Button("Generate FREE")
        btn1.click(free_image_tab, inp1, [out1, img1])
    
    with gr.Tab("🎨 Logo - GH₵5"):
        inp2 = gr.Textbox(label="Business name + style e.g. 'Exquisite cakes, gold logo'")
        pay2 = gr.HTML()
        out2 = gr.Textbox(label="Logo Idea from AI")
        btn2 = gr.Button("Generate Logo Idea - GH₵5")
        btn2.click(logo_tab, inp2, [pay2, out2])
    
    with gr.Tab("📊 Business Presentation - GH₵5"):
        inp3 = gr.Textbox(label="Presentation topic")
        pay3 = gr.HTML()
        out3 = gr.Textbox(label="Presentation Outline", lines=10)
        btn3 = gr.Button("Generate Presentation - GH₵5")
        btn3.click(presentation_tab, inp3, [pay3, out3])
    
    with gr.Tab("🎬 Video Ad - GH₵10"):
        inp4 = gr.Textbox(label="What business is the video for?")
        pay4 = gr.HTML()
        out4 = gr.Textbox(label="Video Script", lines=10)
        aud4 = gr.Audio(label="Voiceover")
        btn4 = gr.Button("Generate Video Ad - GH₵10")
        btn4.click(video_tab, inp4, [pay4, out4, aud4])

    gr.Markdown("Pay with Paystack: MoMo / Card. Contact: raphaeldorgbefu01-dev")

demo.launch()
