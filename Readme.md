<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Live Wallpaper by Team Emogi</title>
</head>
<body style="background-color: #111; color: #ccc; font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px;">
<header style="text-align: center; margin-bottom: 30px;">
        <img src="https://raw.githubusercontent.com/Imimi328/Live-Wallpaper/logo/logo.png" alt="Team Emogi Logo" style="height: 60px; margin-bottom: 10px;">
        <h1 style="color: #4ea3ff;">Live Wallpaper by Team Emogi</h1>
        <p style="font-size: 18px;">Transform your Windows desktop with dynamic video wallpapers!</p>
    </header>
<section>
        <p style="font-size: 16px;">
            Live Wallpaper is an open-source application that allows users to set video files as desktop wallpapers on Windows, with seamless integration, low resource usage, and context-aware audio control. Developed by <strong>Team Emogi</strong>, this project uses Python, PySide6, and MPV to deliver a professional, user-friendly experience.
        </p>
    </section>
<h2 style="color: #4ea3ff;">Features</h2>
    <ul>
        <li><strong>Dynamic Wallpapers</strong>: Set MP4, MKV, AVI, MOV, or WebM videos as your desktop background.</li>
        <li><strong>Context-Aware Audio</strong>: Automatically mutes audio when other applications are in focus.</li>
        <li><strong>Low Resource Usage</strong>: Less than 5% CPU usage with hardware decoding.</li>
        <li><strong>Modern UI</strong>: Includes video previews and system tray integration.</li>
        <li><strong>Looping & Mute Controls</strong>: Easily toggle these settings in the interface.</li>
        <li><strong>Easy Video Management</strong>: Organize videos in a dedicated Wallpapers folder.</li>
    </ul>
<h2 style="color: #4ea3ff;">Installation</h2>
    <h3>Prerequisites</h3>
    <ul>
        <li>Windows 10/11</li>
        <li>Python 3.8+ (recommended via Anaconda)</li>
        <li>MPV Media Player: <a href="https://mpv.io/installation/">Download</a> and add <code>mpv.exe</code> to PATH.</li>
        <li>FFmpeg (optional): For audio detection, add <code>ffprobe.exe</code> to PATH.</li>
    </ul>
<h3>Dependencies</h3>
    <p>Install packages:</p>
    <pre><code>pip install PySide6 psutil pywin32</code></pre>
<h3>Setup</h3>
    <ol>
        <li>Clone the repository:
            <pre><code>git clone https://github.com/Imimi328/Live-Wallpaper.git
cd Live-Wallpaper</code></pre>
        </li>
        <li>Create a Wallpapers directory:
            <pre><code>mkdir Wallpapers</code></pre>
        </li>
        <li>Copy your video files into the Wallpapers folder.</li>
    </ol>
<h2 style="color: #4ea3ff;">Usage</h2>
    <ol>
        <li>Run the application:
            <pre><code>python app.py</code></pre>
        </li>
        <li>Select a video from the list.</li>
        <li>Click "Set Wallpaper" to apply it.</li>
        <li>Uncheck "Mute Video" to allow audio.</li>
        <li>Close the window to minimize to tray. Double-click tray icon to reopen.</li>
    </ol>
<h2 style="color: #4ea3ff;">Troubleshooting</h2>
    <ul>
        <li><strong>MPV Socket Error:</strong> Run as admin, reinstall MPV, or allow it in antivirus.</li>
        <li><strong>High CPU Usage:</strong> Confirm hardware decoding or re-encode videos:
            <pre><code>ffmpeg -i input.mp4 -vcodec h264 -vf scale=1920:1080 -r 30 -acodec aac optimized.mp4</code></pre>
        </li>
        <li><strong>No Audio:</strong> Check for audio track:
            <pre><code>ffprobe -v error -show_streams -select_streams a video.mp4</code></pre>
        </li>
    </ul>
<h2 style="color: #4ea3ff;">Contributing</h2>
    <ol>
        <li>Fork the repository.</li>
        <li>Create a new branch.</li>
        <li>Commit and push your changes.</li>
        <li>Open a pull request.</li>
    </ol>
<h2 style="color: #4ea3ff;">License</h2>
    <p>This project is under the MIT License. See the <a href="LICENSE">LICENSE</a> file.</p>
<h2 style="color: #4ea3ff;">Acknowledgments</h2>
    <ul>
        <li><strong>Ritesh, CEO of Team Emogi</strong>: Project lead and visionary.</li>
        <li><strong>MPV Community</strong>: For the lightweight media player.</li>
        <li><strong>PySide6</strong>: For the Python GUI toolkit.</li>
    </ul>
<footer style="text-align: center; margin-top: 40px; color: #888;">
        <p>Made with ❤️ by Team Emogi</p>
    </footer>

</body>
</html>
