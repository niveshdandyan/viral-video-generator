# Script Templates for Viral Video Generator

## Scene Map Structure

Every video uses a JSON scene map that defines the sequence of scenes, visual prompts, voiceover text, and sound effects.

```json
{
  "scenes": [
    {
      "id": 1,
      "type": "hook",
      "clip": "scene1.mp4",
      "voiceover": "scene1-vo.wav",
      "vo_text": "Narration text for this scene.",
      "visual_prompt": "Detailed visual description for AI video generation. Include camera angle, lighting, mood, and action.",
      "duration": 5,
      "transition": "fade",
      "sfx": [{"type": "whoosh", "offset": 0}]
    }
  ]
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Scene number (sequential, starting at 1) |
| `type` | No | Scene purpose: hook, discovery, demo, feature, payoff, cta |
| `clip` | Yes | Filename for the generated video clip |
| `voiceover` | Yes | Filename for the generated voiceover WAV |
| `vo_text` | Yes | Narration text for text-to-speech |
| `visual_prompt` | Yes | Detailed prompt for AI video generation |
| `duration` | No | Target clip duration in seconds (default: 5) |
| `transition` | No | Transition to next scene: fade, slideright, slideup, slideleft, fadeblack |
| `sfx` | No | Array of sound effects: `[{"type": "whoosh", "offset": 0}]` |

### Available SFX Types

- `whoosh` - Transition swoosh sound
- `boom` - Low impact sound
- `ding` - High bell notification
- `record-scratch` - Comedy record scratch
- `match-ding` - Pleasant two-tone notification
- `heartbeat` - Double thump heartbeat
- `warm-chord` - Pleasant resolution chord

---

## 6-Scene Meme/Promo Template

Best for: product promos, feature showcases, meme-style virals (30-45s)

```json
{
  "scenes": [
    {
      "id": 1,
      "type": "hook",
      "vo_text": "[Relatable problem or funny situation - grab attention in 2 seconds]",
      "visual_prompt": "[Eye-catching visual that sets up the problem]",
      "duration": 5,
      "transition": "fade",
      "sfx": [{"type": "whoosh", "offset": 0}]
    },
    {
      "id": 2,
      "type": "discovery",
      "vo_text": "[Introduce the solution/product - 'Then they discovered...' moment]",
      "visual_prompt": "[Character finding/discovering the solution]",
      "duration": 5,
      "transition": "slideright",
      "sfx": [{"type": "ding", "offset": 0}]
    },
    {
      "id": 3,
      "type": "demo",
      "vo_text": "[Show the product/solution in action - the 'wow' moment]",
      "visual_prompt": "[Product being used, screen recording, or demo visual]",
      "duration": 5,
      "transition": "slideup",
      "sfx": []
    },
    {
      "id": 4,
      "type": "feature",
      "vo_text": "[Key benefit #1 - make it punchy and specific]",
      "visual_prompt": "[Visual showing the specific feature or benefit]",
      "duration": 5,
      "transition": "fade",
      "sfx": [{"type": "whoosh", "offset": 0}]
    },
    {
      "id": 5,
      "type": "payoff",
      "vo_text": "[Emotional resolution - the happy ending, the punchline]",
      "visual_prompt": "[Feel-good visual, success moment, or comedy payoff]",
      "duration": 5,
      "transition": "fade",
      "sfx": [{"type": "warm-chord", "offset": 0}]
    },
    {
      "id": 6,
      "type": "cta",
      "vo_text": "[Call to action - short, direct, memorable]",
      "visual_prompt": "[Brand/product logo, URL, or final visual with text overlay]",
      "duration": 5,
      "transition": "fadeblack",
      "sfx": [{"type": "ding", "offset": 0}]
    }
  ]
}
```

---

## 8-Scene Story Template

Best for: narrative videos, character-driven content, mini-stories (50-70s)

```json
{
  "scenes": [
    {
      "id": 1,
      "type": "hook",
      "vo_text": "[Introduce character and their problem - make audience relate instantly]",
      "visual_prompt": "[Character in their current situation, show emotion]",
      "duration": 5,
      "transition": "fade",
      "sfx": [{"type": "whoosh", "offset": 0}]
    },
    {
      "id": 2,
      "type": "context",
      "vo_text": "[Deepen the problem - why it matters, what's at stake]",
      "visual_prompt": "[Show the struggle, the failed attempts]",
      "duration": 5,
      "transition": "slideright",
      "sfx": []
    },
    {
      "id": 3,
      "type": "discovery",
      "vo_text": "[The turning point - character finds the solution]",
      "visual_prompt": "[Moment of discovery, light bulb moment]",
      "duration": 5,
      "transition": "slideup",
      "sfx": [{"type": "ding", "offset": 0}]
    },
    {
      "id": 4,
      "type": "demo",
      "vo_text": "[Solution in action - show don't tell]",
      "visual_prompt": "[Product/solution being used, detailed view]",
      "duration": 5,
      "transition": "fade",
      "sfx": []
    },
    {
      "id": 5,
      "type": "feature1",
      "vo_text": "[First amazing result or feature]",
      "visual_prompt": "[Visual proof of the first benefit]",
      "duration": 5,
      "transition": "slideright",
      "sfx": [{"type": "whoosh", "offset": 0}]
    },
    {
      "id": 6,
      "type": "feature2",
      "vo_text": "[Second amazing result - build momentum]",
      "visual_prompt": "[Visual proof of the second benefit]",
      "duration": 5,
      "transition": "slideup",
      "sfx": [{"type": "whoosh", "offset": 0}]
    },
    {
      "id": 7,
      "type": "payoff",
      "vo_text": "[Emotional climax - character achieves their goal]",
      "visual_prompt": "[Happy ending, celebration, success moment]",
      "duration": 5,
      "transition": "fade",
      "sfx": [{"type": "warm-chord", "offset": 0}]
    },
    {
      "id": 8,
      "type": "cta",
      "vo_text": "[Tag line + call to action]",
      "visual_prompt": "[Brand/product final shot, memorable closing visual]",
      "duration": 5,
      "transition": "fadeblack",
      "sfx": [{"type": "ding", "offset": 0}]
    }
  ]
}
```

---

## Visual Prompt Tips

### For AI Video Generation (Veo 3.1)
- Be specific about camera angle: "close-up", "wide shot", "aerial view"
- Describe lighting: "warm golden hour", "neon-lit", "soft studio lighting"
- Include motion: "camera slowly zooms in", "panning left to right"
- Set the mood: "cinematic", "playful", "dramatic"
- For vertical video: subjects should be centered, avoid wide horizontal compositions

### Example Visual Prompts

**Character scene:**
> "Close-up of a cute fluffy capybara sitting alone by a sunset pond, looking sad but adorable. Warm golden hour lighting, shallow depth of field, cinematic color grading. 9:16 vertical format."

**Tech/product scene:**
> "A futuristic holographic interface floating in mid-air showing a website being built in real-time, glowing blue and purple code streams flowing across the screen. Dark background, neon lighting, cinematic."

**Action scene:**
> "A capybara typing rapidly on a glowing laptop keyboard, code and sparkles flying from the screen, energetic and exciting. Bright colorful lighting, medium shot, dynamic camera angle."

**Emotional payoff:**
> "Two capybaras sitting together by a beautiful sunset pond, looking happy and content. Cherry blossom petals falling, warm pastel colors, romantic lighting, slow motion."

---

## Voiceover Writing Tips

- **Keep it punchy**: Short sentences. Maximum 15 words per sentence.
- **Use pauses**: Period = short pause. Ellipsis = dramatic pause.
- **Be conversational**: Write like you're talking to a friend.
- **Comedy timing**: Set up... then deliver. The pause does the work.
- **Numbers are powerful**: "In 30 seconds" beats "very quickly".
- **End strong**: Last line should be memorable, quotable, or actionable.

### Length Guide (Piper TTS @ default speed)
- 5-word sentence: ~2 seconds
- 10-word sentence: ~3.5 seconds
- 15-word sentence: ~5 seconds
- Target: 8-12 words per scene for punchy delivery

---

## Using Screenshots for Real Product Scenes

When you need to show a real website or product interface, use a screenshot with the Ken Burns effect instead of AI-generated video:

```bash
# Download a screenshot or use an existing one
curl -sL "https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg" -o screenshot.jpg

# Create Ken Burns effect video (slow zoom + pan)
FFMPEG="/tmp/ffmpeg-7.0.2-amd64-static/ffmpeg"
DURATION=10  # Match voiceover duration
FRAMES=$((DURATION * 30))  # 30fps

$FFMPEG -y -loop 1 -i screenshot.jpg -t $DURATION \
  -vf "scale=2160:3840,zoompan=z='min(zoom+0.0012,1.35)':x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':d=$FRAMES:s=1080x1920:fps=30,format=yuv420p" \
  -c:v libx264 -preset fast -crf 23 \
  scene-screenshot.mp4
```

This creates a cinematic slow-zoom effect on the screenshot, making static images feel dynamic for the video.
