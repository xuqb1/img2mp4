# imgs2mp4

Convert a series of images into an MP4 video with a simple drag-and-drop GUI. 

---

## Features
- Drag & drop images (PNG/JPG/JPEG)  
- Re-order, delete, preview in GUI  
- Custom FPS & output name  
- One-click generate MP4 (H.264)  
- Portable executable 

---

## Quick Start

### 1) Download ready-to-run executable
Go to [Releases](https://github.com/xuqb1/imgs2mp4/releases) → unzip → run `img2mp4.exe`

### 2) Run from source
```bash
# Python ≥ 3.8 (3.12 recommended)
git clone https://github.com/xuqb1/img2mp4.git
cd img2mp4
pip install pyinstaller pillow tkinterdnd2
python img2mp4.py
```

### 3) Build portable EXE yourself
```bash
pip install pyinstaller pillow tkinterdnd2
pyinstaller -F -w -i app.ico --hidden-import tkinterdnd2 img2mp4_gui.py
# dist/imgs2mp4.exe  generated
```

## Screenshot
![Main Window](screenshots/work-window.png)

## Requirements
- pillow
- tkinterdnd2

---

## License
MIT © 2026 xuqb1
