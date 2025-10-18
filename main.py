import os
import uuid
import shutil
import threading
import time
import psutil
from flask import Flask, request, render_template, session, jsonify, url_for,redirect
from werkzeug.utils import secure_filename
from colorizator import MangaColorizator
from inference import colorize_single_image

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for session management

# Base folder for temporary session files
SESSION_BASE = "static/tmp_sessions"
os.makedirs(SESSION_BASE, exist_ok=True)

# Args class for colorization parameters
class Args:
    def __init__(self, gpu=False, denoiser=True, denoiser_sigma=25, size=576):
        self.gpu = gpu
        self.denoiser = denoiser
        self.denoiser_sigma = denoiser_sigma
        self.size = size
        self.generator = "networks/generator.zip"
        self.extractor = "networks/extractor.pth"

args = Args()
device = "cpu"
colorizer = MangaColorizator(device, args.generator, None)

# Resource monitoring functions
def monitor_usage(log_interval=1):
    """Background thread to monitor CPU and memory."""
    process = psutil.Process(os.getpid())
    start_time = time.time()
    cpu_readings, mem_readings = [], []

    while getattr(threading.current_thread(), "running", True):
        cpu = process.cpu_percent(interval=None)
        mem = process.memory_info().rss / (1024 ** 2)
        cpu_readings.append(cpu)
        mem_readings.append(mem)
        print(f"[Monitor] CPU: {cpu:.1f}% | Memory: {mem:.1f} MB")
        time.sleep(log_interval)

    avg_cpu = sum(cpu_readings) / len(cpu_readings) if cpu_readings else 0
    peak_mem = max(mem_readings) if mem_readings else 0
    duration = time.time() - start_time

    est_power_watts = 45 * (avg_cpu / 100)  # Rough CPU power estimate
    est_energy_wh = est_power_watts * (duration / 3600)

    print("\n--- Resource Summary ---")
    print(f"Average CPU: {avg_cpu:.1f}%")
    print(f"Peak Memory: {peak_mem:.1f} MB")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Estimated Energy Used: {est_energy_wh:.3f} Wh\n")

def run_with_monitor(target_func):
    monitor = threading.Thread(target=monitor_usage, daemon=True)
    monitor.running = True
    monitor.start()
    start = time.time()
    try:
        target_func()
    finally:
        monitor.running = False
        monitor.join()
        print(f"Total elapsed time: {time.time() - start:.1f}s")

# Session workspace
def get_user_workspace():
    if "workspace_id" not in session:
        session["workspace_id"] = str(uuid.uuid4())
    workspace_id = session["workspace_id"]
    upload_dir = os.path.join(SESSION_BASE, workspace_id, "uploads")
    colorized_dir = os.path.join(SESSION_BASE, workspace_id, "colorized")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(colorized_dir, exist_ok=True)
    return upload_dir, colorized_dir

def cleanup_workspace():
    workspace_id = session.get("workspace_id")
    if workspace_id:
        base_dir = os.path.join(SESSION_BASE, workspace_id)
        shutil.rmtree(base_dir, ignore_errors=True)
        session.pop("workspace_id", None)

# Flask routes
@app.route("/", methods=["GET", "POST"])
def index():
    upload_dir, colorized_dir = get_user_workspace()

    # Upload images (AJAX-enabled)
    if request.method == "POST" and request.form.get("action") != "colorize_ajax":
        files = request.files.getlist("images")
        uploaded_files = []
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_path = os.path.join(upload_dir, filename)
                file.save(upload_path)
                uploaded_files.append(filename)
        if request.is_json or request.form.get("ajax"):
            return {
                "uploaded": uploaded_files,
                "upload_folder": url_for('static', filename=f"tmp_sessions/{session['workspace_id']}/uploads")
            }
        return redirect(url_for("index"))

    # AJAX colorize request
    if request.method == "POST" and request.form.get("action") == "colorize_ajax":
        img_name = request.form.get("img_name")
        if not img_name:
            return jsonify({"error": "No image specified"}), 400

        upload_path = os.path.join(upload_dir, img_name)
        name, _ = os.path.splitext(img_name)
        colorized_filename = f"{name}_colorized.png"
        colorized_path = os.path.join(colorized_dir, colorized_filename)

        if not os.path.exists(colorized_path):
            # Run colorization with monitoring
            run_with_monitor(lambda: colorize_single_image(upload_path, colorized_path, colorizer, args))

        colorized_url = url_for("static", filename=f"tmp_sessions/{session['workspace_id']}/colorized/{colorized_filename}")
        return jsonify({"colorized": colorized_url})

    # Prepare image pairs for rendering
    uploaded_images = sorted(os.listdir(upload_dir)) if os.path.exists(upload_dir) else []
    colorized_images = sorted(os.listdir(colorized_dir)) if os.path.exists(colorized_dir) else []
    pairs = []
    for up_img in uploaded_images:
        name, _ = os.path.splitext(up_img)
        col_img = f"{name}_colorized.png"
        col_path = col_img if col_img in colorized_images else None
        pairs.append((up_img, col_path))

    return render_template("index.html", pairs=pairs)

# AJAX delete image
@app.route("/delete_image", methods=["POST"])
def delete_image():
    upload_dir, colorized_dir = get_user_workspace()
    img_name = request.form.get("img_name")
    if not img_name:
        return jsonify({"error": "No image specified"}), 400

    upload_path = os.path.join(upload_dir, img_name)
    if os.path.exists(upload_path):
        os.remove(upload_path)

    name, _ = os.path.splitext(img_name)
    colorized_filename = f"{name}_colorized.png"
    colorized_path = os.path.join(colorized_dir, colorized_filename)
    if os.path.exists(colorized_path):
        os.remove(colorized_path)

    return jsonify({"success": True})

# Optional endpoint to end session
@app.route("/end_session")
def end_session():
    cleanup_workspace()
    return "Session ended and all images deleted."

if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=8080))
