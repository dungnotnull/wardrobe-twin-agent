@echo off
REM wardrobe-twin-agent setup script for Windows
REM Run this once after cloning the repository.

echo =============================================
echo   wardrobe-twin-agent - Setup (Windows)
echo =============================================
echo.

echo ^>>> Setting up Python virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat

echo ^>>> Installing core Python dependencies (lightweight)...
pip install -e .

echo.
echo ^>>> Optional: Install heavy ML dependencies for full features:
echo     pip install -e ".[ml-heavy]"
echo     This includes: mediapipe, segment-anything, scikit-learn
echo     Note: detectron2 requires special install on Windows.
echo     See: https://detectron2.readthedocs.io/en/latest/tutorials/install.html
echo.

echo ^>>> Setting up Electron + React UI...
cd ui
call npm install
cd ..

echo.
echo ^>>> Creating data directories...
if not exist "data\models" mkdir "data\models"
if not exist "data\avatars" mkdir "data\avatars"
if not exist "data\wardrobe_images" mkdir "data\wardrobe_images"
if not exist "data\cache" mkdir "data\cache"

echo.
echo ^>>> Copying .env template...
if not exist ".env" (
    copy .env.example .env
    echo     Created .env - edit it to add your API keys
) else (
    echo     .env already exists, keeping it
)

echo.
echo =============================================
echo   Setup complete!
echo =============================================
echo.
echo   To start the backend:
echo     .venv\Scripts\Activate.ps1
echo     python -m backend.api.server
echo.
echo   To start the UI:
echo     cd ui ^&^& npm run dev
echo.
echo   To load the browser extension:
echo     1. Open Chrome -^> chrome://extensions
echo     2. Enable Developer mode
echo     3. Load unpacked -^> select the extension\ folder
echo.
echo   API keys (optional, for LLM advisor):
echo     Edit .env and add your ANTHROPIC_API_KEY and/or OPENAI_API_KEY
echo.
pause
