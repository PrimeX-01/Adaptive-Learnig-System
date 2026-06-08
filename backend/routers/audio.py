from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import io
import requests
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (parent directory of backend)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from db.database import get_db
from sqlalchemy.orm import Session
from auth import get_current_student

router = APIRouter(prefix='/api/audio', tags=['Audio'])

class TTSRequest(BaseModel):
    text: str
    voice_id: Optional[str] = '21m00Tcm4TlvDq8ikWAM'  # Rachel voice ID (ElevenLabs default)

@router.post('/speak')
async def text_to_speech(
    req: TTSRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_student)
):
    api_key = os.getenv('ELEVENLABS_API_KEY')
    print(f"[DEBUG] API key loaded: {bool(api_key)}")
    if not api_key:
        raise HTTPException(status_code=501, detail="No ElevenLabs API key configured")

    # Limit text length to stay within free tier (10k characters)
    text = req.text[:5000]
    
    # Use the provided voice_id or fallback to Rachel
    voice_id = req.voice_id
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }
    
    data = {
        "text": text,
        "model_id": "eleven_flash_v2_5",   # Fast, high-quality model
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5,
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Return the audio as a streaming response
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )
    except requests.exceptions.HTTPError as e:
        print(f"[TTS HTTP Error] {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=500, detail=f"TTS API error: {e.response.status_code}")
    except Exception as e:
        print(f"[TTS Error] {e}")
        raise HTTPException(status_code=500, detail="TTS generation failed")