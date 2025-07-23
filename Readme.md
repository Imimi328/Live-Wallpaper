<html lang="en">
<body className="bg-gray-900 text-gray-200 font-sans">
    <div className="container mx-auto p-6 max-w-4xl">
        <header className="text-center mb-8">
            <img src=/blob/logo/logo.png" alt="Team Emogi Logo" className="mx-auto h-24 mb-4">
            <h1 className="text-4xl font-bold text-blue-400">Live Wallpaper by Team Emogi</h1>
            <p className="text-xl mt-2">Transform your Windows desktop with dynamic video wallpapers!</p>
        </header>
      <section className="mb-8">
            <p className="text-lg">
                Live Wallpaper is an open-source application that allows users to set video files as desktop wallpapers on Windows, with seamless integration, low resource usage, and context-aware audio control. Developed by <strong>Team Emogi</strong>, this project leverages Python, PySide6, and MPV to deliver a professional, user-friendly experience.
            </p>
        </section>
<section className="mb-8">
            <h2 className="text-2xl font-semibold text-blue-300 mb-4">Features</h2>
            <ul className="list-disc pl-6 space-y-2">
                <li><strong>Dynamic Wallpapers</strong>: Set MP4, MKV, AVI, MOV, or WebM videos as your desktop background.</li>
                <li><strong>Context-Aware Audio</strong>: Automatically mutes audio when other applications are in focus, unmuting when the desktop is active.</li>
                <li><strong>Low Resource Usage</strong>: Achieves &lt;5% CPU usage with hardware-accelerated decoding (DXVA2).</li>
                <li><strong>Modern UI</strong>: Dark-themed interface with video previews, system tray integration, and persistent settings.</li>
                <li><strong>Looping & Mute Controls</strong>: Toggle video looping and audio mute states via the GUI.</li>
                <li><strong>Easy Video Management</strong>: Add videos to a dedicated Wallpapers directory.</li>
            </ul>
        </section>

 <section className="mb-8">
            <h2 className="text-2xl font-semibold text-blue-300 mb-4">Installation</h2>
            <h3 className="text-xl font-medium mb-2">Prerequisites</h3>
            <ul className="list-disc pl-6 space-y-2">
                <li><strong>Windows 10/11</strong></li>
                <li><strong>Python 3.8+</strong> (e.g., via Anaconda)</li>
                <li><strong>MPV Media Player</strong>: Download from <a href="https://mpv.io/installation/" className="text-blue-400 hover:underline">mpv.io</a> and add <code>mpv.exe</code> to <code>PATH</code> or the project directory.</li>
                <li><strong>FFmpeg</strong> (optional, for audio track detection): Add <code>ffprobe.exe</code> to <code>PATH</code>.</li>
            </ul>
            <h3 className="text-xl font-medium mt-4 mb-2">Dependencies</h3>
            <p>Install required Python packages:</p>
            <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg"><code>pip install PySide6 psutil pywin32</code></pre>
            <h3 className="text-xl font-medium mt-4 mb-2">Setup</h3>
            <ol className="list-decimal pl-6 space-y-2">
                <li>Clone the repository:
                    <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg"><code>git clone https://github.com/Imimi328/Live-Wallpaper.git
cd Live-Wallpaper</code></pre>
                </li>
                <li>Create a <code>Wallpapers</code> directory:
                    <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg"><code>mkdir Wallpapers</code></pre>
                </li>
                <li>Copy video files (e.g., <code>video.mp4</code>) to the <code>Wallpapers</code> directory.</li>
            </ol>
        </section>
<section className="mb-8">
            <h2 className="text-2xl font-semibold text-blue-300 mb-4">Usage</h2>
            <ol className="list-decimal pl-6 space-y-2">
                <li>Run the application:
                    <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg"><code>python app.py</code></pre>
                </li>
                <li><strong>Select a Video</strong>: Choose a video from the listbox to preview.</li>
                <li><strong>Set Wallpaper</strong>: Click "Set Wallpaper" to apply the video as your desktop background.</li>
                <li><strong>Toggle Audio</strong>: Uncheck "Mute Video" to enable audio when the desktop is active.</li>
                <li><strong>Minimize to Tray</strong>: Close the window to minimize to the system tray; double-click the tray icon to restore.</li>
            </ol>
        </section>
 <section className="mb-8">
            <h2 className="text-2xl font-semibold text-blue-300 mb-4">Troubleshooting</h2>
            <ul className="list-disc pl-6 space-y-2">
                <li><strong>MPV Socket Failure</strong> (<code>[ERROR] MPV socket \\.\pipe\mpvpipe not created</code>):
                    <ul className="list-circle pl-6 space-y-1">
                        <li>Run as administrator.</li>
                        <li>Reinstall MPV from <a href="https://mpv.io/installation/" className="text-blue-400 hover:underline">mpv.io</a>.</li>
                        <li>Disable antivirus or add exceptions for <code>mpv.exe</code>.</li>
                        <li>Check <code>C:\Users\&lt;YourUser&gt;\AppData\Local\Temp\mpv_debug_&lt;pid&gt;.log</code> for errors.</li>
                        <li>Test MPV IPC:
                            <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg"><code>mpv --input-ipc-server=\\.\pipe\mpvpipe --msg-level=all=debug Wallpapers/your-video.mp4</code></pre>
                        </li>
                    </ul>
                </li>
                <li><strong>High CPU Usage</strong>:
                    <ul className="list-circle pl-6 space-y-1">
                        <li>Ensure <code>[INFO] Hardware decoding confirmed</code> in console logs.</li>
                        <li>Re-encode high-resolution videos:
                            <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg"><code>ffmpeg -i Wallpapers/input.mp4 -vcodec h264 -vf scale=1920:1080 -r 30 -acodec aac Wallpapers/optimized.mp4</code></pre>
                        </li>
                    </ul>
                </li>
                <li><strong>No Audio</strong>:
                    <ul className="list-circle pl-6 space-y-1">
                        <li>Verify the video has an audio track:
                            <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg"><code>ffprobe -v error -show_streams -select_streams a Wallpapers/your-video.mp4</code></pre>
                        </li>
                        <li>Ensure <code>pywin32</code> is installed:
                            <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg"><code>pip install pywin32</code></pre>
                        </li>
                    </ul>
                </li>
            </ul>
        </section>

<section className="mb-8">
            <h2 className="text-2xl font-semibold text-blue-300 mb-4">Contributing</h2>
            <p>Contributions are welcome! Please:</p>
            <ol className="list-decimal pl-6 space-y-2">
                <li>Fork the repository.</li>
                <li>Create a feature branch (<code>git checkout -b feature/YourFeature</code>).</li>
                <li>Commit changes (<code>git commit -m "Add YourFeature"</code>).</li>
                <li>Push to the branch (<code>git push origin feature/YourFeature</code>).</li>
                <li>Open a pull request.</li>
            </ol>
        </section>
<section className="mb-8">
            <h2 className="text-2xl font-semibold text-blue-300 mb-4">License</h2>
            <p>This project is licensed under the MIT License. See the <a href="LICENSE" className="text-blue-400 hover:underline">LICENSE</a> file for details.</p>
        </section>
 <section className="mb-8">
            <h2 className="text-2xl font-semibold text-blue-300 mb-4">Acknowledgments</h2>
            <ul className="list-disc pl-6 space-y-2">
                <li><strong>Ritesh, CEO of Team Emogi</strong>: Project lead and visionary.</li>
                <li><strong>MPV Community</strong>: For the lightweight, powerful media player.</li>
                <li><strong>PySide6</strong>: For the robust GUI framework.</li>
            </ul>
        </section>
<footer className="text-center mt-8 text-gray-400">
            <p>Made with ❤️ by Team Emogi</p>
        </footer>
    </div>
</body>
</html>
