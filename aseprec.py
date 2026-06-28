import os
import sys
import time
import requests
import socket
import dns.resolver
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from googlesearch import search

# Tambahkan go bin path ke PATH agar tool go bisa terdeteksi
go_bin_path = os.path.expanduser("~/go/bin")
if go_bin_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + go_bin_path

console = Console()

def banner():
    ascii_art = """
     █████╗ ███████╗███████╗██████╗ ███████╗ ██████╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗████╗  ██║
    ███████║███████╗█████╗  ██████╔╝███████╗██║     ███████║██╔██╗ ██║
    ██╔══██║╚════██║██╔══╝  ██╔═══╝ ╚════██║██║     ██╔══██║██║╚██╗██║
    ██║  ██║███████║███████╗██║     ███████║╚██████╗██║  ██║██║ ╚████║
    ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝
    """
    console.print(Panel.fit(ascii_art, title="ASEPSCAN", style="cyan"))
    console.print(f"[bold yellow]Versi 5.0 | Ultimate Recon Tool[/bold yellow]\n")
    console.print(f"[bold green]Fitur Baru:[/bold green] DNS Recon + Email Harvester + Cloud Detector + CMS Detector + Port Scanner\n")

def get_install_command(package_name):
    is_termux = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux/files/usr/bin')
    if is_termux:
        return f"pkg install -y {package_name}"
    else:
        # Check package managers
        if os.system("command -v apt > /dev/null 2>&1") == 0:
            return f"sudo apt install -y {package_name}"
        elif os.system("command -v pacman > /dev/null 2>&1") == 0:
            return f"sudo pacman -S {package_name}"
        elif os.system("command -v dnf > /dev/null 2>&1") == 0:
            return f"sudo dnf install -y {package_name}"
        else:
            return f"installer package manager Anda untuk {package_name}"

def check_tool(tool_name, install_instruksi):
    if os.system(f"command -v {tool_name} > /dev/null") != 0:
        console.print(Panel.fit(
            f"{tool_name} gak ada di sistem.\nInstall pake: {install_instruksi}",
            title=f"{tool_name} Error", style="red"))
        return False
    return True

def detect_protocol(target):
    try:
        https_check = os.popen(f"curl -Is https://{target} | head -n 1").read()
        if "200" in https_check or "301" in https_check or "302" in https_check:
            return "https"
    except:
        pass
    return "http"

def whois_lookup(target):
    if not check_tool("whois", get_install_command("whois")):
        return
    console.print("[yellow]⏳ Ngecek WHOIS...[/yellow]")
    result = os.popen(f"whois {target}").read()
    console.print(Panel.fit(result, title="Hasil WHOIS", style="green"))

def whatweb_scan(target):
    if not check_tool("whatweb", get_install_command("whatweb")):
        return
    console.print("[yellow]⏳ Ngecek WhatWeb...[/yellow]")
    result = os.popen(f"whatweb {target}").read()
    console.print(Panel.fit(result, title="Hasil WhatWeb", style="green"))

def nmap_scan(target, mode="cepat"):
    if not check_tool("nmap", get_install_command("nmap")):
        return
    console.print(f"[yellow]⏳ Ngecek Nmap ({mode})...[/yellow]")
    scan_type = "-Pn -sV -T4" if mode == "lengkap" else "-Pn -T4 -F"
    result = os.popen(f"nmap {scan_type} {target}").read()
    console.print(Panel.fit(result, title="Hasil Nmap", style="green"))

def subdomain_checker(target):
    if not check_tool("assetfinder", "go install github.com/tomnomnom/assetfinder@latest"):
        return
    console.print("[yellow]⏳ Nyari subdomain...[/yellow]")
    result = os.popen(f"assetfinder --subs-only {target}").read()
    panel_text = result.strip() if result.strip() else "Gak nemu subdomain."
    console.print(Panel.fit(panel_text, title="Subdomain", style="green"))

def gobuster_scan(target):
    if not check_tool("gobuster", "go install github.com/OJ/gobuster/v3@latest"):
        return

    protocol = detect_protocol(target)
    wordlist_path = os.path.expanduser("~/.wordlists/common.txt")
    
    if not os.path.exists(wordlist_path):
        console.print("[blue]Wordlist gak ada, download dulu...[/blue]")
        os.makedirs(os.path.dirname(wordlist_path), exist_ok=True)
        os.system(f"curl -s -o {wordlist_path} https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt")
        if not os.path.exists(wordlist_path):
            console.print("[red]Gagal download wordlist. Cek koneksi internet.[/red]")
            return
        console.print("[green]✓ Wordlist udah didownload[/green]")

    console.print("[yellow]⏳ Jalanin Gobuster...[/yellow]")
    command = f"gobuster dir -u {protocol}://{target} -w {wordlist_path} -t 50 -b 404,403"
    
    with console.status("[bold green]Scanning direktori...", spinner="dots"):
        raw_result = os.popen(command).read()

    if not raw_result.strip():
        console.print(Panel.fit("Gak nemu direktori menarik", title="Hasil Gobuster", style="green"))
        return

    status_colors = {
        "200": "bold green", "204": "bold bright_green", "301": "bold cyan",
        "302": "bold blue", "403": "bold red", "401": "bold magenta", "500": "bold yellow"
    }

    lines = raw_result.strip().split("\n")
    display_lines = []
    for line in lines:
        colored_line = line
        for status, color in status_colors.items():
            if f"Status: {status}" in line:
                colored_line = f"[{color}]{line}[/]"
                break
        display_lines.append(colored_line)

    console.print(Panel.fit("\n".join(display_lines), title="Hasil Gobuster", style="green"))

def cek_header(target):
    console.print("[yellow]⏳ Ngecek header HTTP...[/yellow]")
    protocol = detect_protocol(target)
    result = os.popen(f"curl -I {protocol}://{target}").read()
    panel_text = result if result else "Server gak ngasih respons."
    console.print(Panel.fit(panel_text, title="Header HTTP", style="green"))

def waf_detection(target):
    pip_install_suffix = " --break-system-packages" if sys.prefix == sys.base_prefix else ""
    if not check_tool("wafw00f", "pip install wafw00f" + pip_install_suffix):
        return
    console.print("[yellow]⏳ Ngecek WAF...[/yellow]")
    result = os.popen(f"wafw00f {target}").read()
    console.print(Panel.fit(result.strip(), title="Deteksi WAF", style="green"))

def screenshot_web(target):
    pip_install_suffix = " --break-system-packages" if sys.prefix == sys.base_prefix else ""
    if not check_tool("webscreenshot", "pip install webscreenshot" + pip_install_suffix):
        return
    protocol = detect_protocol(target)
    outdir = f"screenshot_{target.replace('.', '_')}"
    console.print(f"[yellow]📸 Ngambil screenshot {protocol}://{target}...[/yellow]")
    os.system(f"webscreenshot -o {outdir} {protocol}://{target} > /dev/null 2>&1")
    console.print(f"[green]✓ Screenshot disimpen di: [bold]{outdir}[/bold][/green]")

def userrecon_scan(username):
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
    
    results = []
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Cek platform...", total=len(platforms))
        
        for platform, url in platforms.items():
            progress.update(task, advance=1, description=f"[cyan]Cek {platform}...")
            
            try:
                response = requests.head(url, timeout=5, allow_redirects=True)
                status = response.status_code
                
                if status == 200:
                    results.append(f"[green]✓ [bold]{platform}[/bold]: Ditemukan ({url})")
                elif status == 404:
                    results.append(f"[red]✗ [bold]{platform}[/bold]: Tidak ditemukan")
                else:
                    results.append(f"[yellow]? [bold]{platform}[/bold]: Status {status} ({url})")
                
            except requests.exceptions.RequestException:
                results.append(f"[yellow]? [bold]{platform}[/bold]: Gagal koneksi")
    
    console.print(Panel.fit("\n".join(results), title=f"Hasil UserRecon: {username}", style="cyan"))

def godorker_scan(target):
    console.print(f"[yellow]⏳ Menjalankan GoDorker untuk [bold]{target}[/bold]...[/yellow]")
    
    dorks = [
        f"site:{target} inurl:admin",
        f"site:{target} intext:password",
        f"site:{target} ext:pdf",
        f"site:{target} ext:doc | ext:docx",
        f"site:{target} inurl:login",
        f"site:{target} intitle:index.of",
        f"site:{target} ext:sql",
        f"site:{target} filetype:env",
        f"site:{target} inurl:wp-admin",
        f"site:{target} inurl:config",
        f"site:{target} ext:log",
        f"site:{target} intext:username",
        f"site:{target} inurl:backup",
        f"site:{target} inurl:phpmyadmin",
        f"site:{target} intext:api key"
    ]
    
    results = []
    
    with console.status("[bold green]Googling dork...", spinner="earth") as status:
        for i, dork in enumerate(dorks):
            status.update(status=f"[bold green]Dorking ({i+1}/{len(dorks)})...")
            
            try:
                # Menggunakan modul googlesearch untuk mendapatkan hasil
                for url in search(dork, num_results=3):
                    results.append(f"[cyan]- [link={url}]{url}[/link]")
            except Exception as e:
                results.append(f"[red]Error pada dork '{dork}': {str(e)}")
    
    if results:
        console.print(Panel.fit("\n".join(results), title=f"Hasil GoDorker: {target}", style="green"))
    else:
        console.print(Panel.fit("Tidak ditemukan hasil untuk dork yang diberikan", title="Hasil GoDorker", style="yellow"))

def dns_recon(target):
    console.print(f"[yellow]⏳ Melakukan DNS Recon untuk [bold]{target}[/bold]...[/yellow]")
    
    record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA']
    results = []
    
    try:
        for rtype in record_types:
            try:
                answers = dns.resolver.resolve(target, rtype)
                results.append(f"[bold magenta]╔═ {rtype} Records:[/bold magenta]")
                for rdata in answers:
                    results.append(f"[bold cyan]║[/bold cyan] {rdata.to_text()}")
            except dns.resolver.NoAnswer:
                pass
            except dns.resolver.NXDOMAIN:
                results.append(f"[bold red]║ Domain tidak ditemukan![/bold red]")
                break
            except Exception as e:
                results.append(f"[bold yellow]║ Error: {str(e)}[/bold yellow]")
    except dns.resolver.NoNameservers:
        results.append("[bold red]║ Tidak ada nameserver yang merespons[/bold red]")
    
    if len(results) > 0:
        console.print(Panel.fit("\n".join(results), title="Hasil DNS Recon", style="green"))
    else:
        console.print(Panel.fit("Tidak ada record DNS yang ditemukan", title="Hasil DNS Recon", style="yellow"))

def email_harvester(target):
    console.print(f"[yellow]⏳ Mencari email terkait [bold]{target}[/bold]...[/yellow]")
    
    sources = [
        "https://www.google.com/search?q=%40{}",
        "https://www.bing.com/search?q=%40{}",
        "https://search.yahoo.com/search?p=%40{}"
    ]
    
    emails = set()
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Mencari email...", total=len(sources))
        
        for url_template in sources:
            try:
                url = url_template.format(target)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(url, headers=headers, timeout=10)
                
                # Regex sederhana untuk mencari email
                import re
                found_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', response.text)
                
                for email in found_emails:
                    if target in email:
                        emails.add(email)
                
                progress.update(task, advance=1)
            except Exception as e:
                progress.update(task, advance=1)
    
    if emails:
        email_list = "\n".join([f"[green]• {email}[/green]" for email in emails])
        console.print(Panel.fit(email_list, title="Email Ditemukan", style="green"))
    else:
        console.print(Panel.fit("Tidak ditemukan email terkait domain ini", title="Email Harvester", style="yellow"))

def cloud_detector(target):
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
    
    protocol = detect_protocol(target)
    results = []
    
    try:
        response = requests.get(f"{protocol}://{target}", timeout=10)
        headers = response.headers
        
        for cloud, indicators in cloud_indicators.items():
            for indicator in indicators:
                if indicator in response.text.lower() or any(indicator in value.lower() for value in headers.values()):
                    results.append(f"[green]✓ {cloud}[/green]")
                    break
            else:
                results.append(f"[red]✗ {cloud}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return
    
    if results:
        console.print(Panel.fit("\n".join(results), title="Hasil Cloud Detector", style="cyan"))
    else:
        console.print(Panel.fit("Tidak terdeteksi layanan cloud", title="Cloud Detector", style="yellow"))

def cms_detector(target):
    console.print(f"[yellow]⏳ Mendeteksi CMS untuk [bold]{target}[/bold]...[/yellow]")
    
    cms_indicators = {
        "WordPress": ["wp-content", "wp-includes", "wordpress"],
        "Joomla": ["joomla", "media/system/js", "index.php?option=com"],
        "Drupal": ["drupal", "sites/all/themes", "core/misc/drupal.js"],
        "Magento": ["magento", "/js/mage/", "skin/frontend"],
        "Shopify": ["shopify", "cdn.shopify.com", "shopify.shop"],
        "PrestaShop": ["prestashop", "modules/", "themes/"],
        "OpenCart": ["opencart", "catalog/view/theme", "system/"],
        "WooCommerce": ["woocommerce", "wc-", "wp-content/plugins/woocommerce"],
        "Laravel": ["laravel", "/vendor/laravel", "mix-manifest.json"]
    }
    
    protocol = detect_protocol(target)
    results = []
    
    try:
        response = requests.get(f"{protocol}://{target}", timeout=10)
        content = response.text.lower()
        
        for cms, indicators in cms_indicators.items():
            for indicator in indicators:
                if indicator in content:
                    results.append(f"[green]✓ {cms}[/green]")
                    break
            else:
                results.append(f"[red]✗ {cms}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return
    
    if any("✓" in result for result in results):
        detected = [r for r in results if "✓" in r]
        console.print(Panel.fit("\n".join(detected), title="CMS Terdeteksi", style="green"))
    else:
        console.print(Panel.fit("Tidak terdeteksi CMS populer", title="CMS Detector", style="yellow"))

def port_scanner(target):
    console.print(f"[yellow]⏳ Scanning port untuk [bold]{target}[/bold]...[/yellow]")
    
    common_ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 
                    993, 995, 1723, 3306, 3389, 5900, 8080, 8443]
    
    open_ports = []
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Scanning port...", total=len(common_ports))
        
        for port in common_ports:
            progress.update(task, advance=1, description=f"[cyan]Scan port {port}...")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            try:
                result = sock.connect_ex((target, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except:
                pass
    
    if open_ports:
        ports_list = "\n".join([f"[green]• Port {port} terbuka[/green]" for port in open_ports])
        console.print(Panel.fit(ports_list, title="Port Terbuka", style="green"))
    else:
        console.print(Panel.fit("Tidak ada port terbuka yang ditemukan", title="Port Scanner", style="yellow"))

def menu():
    banner()
    
    while True:
        table = Table(title="Menu Tools Recon", header_style="bold magenta", show_lines=True)
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
        table.add_row("10", "GoDorker", "Google Dorking otomatis")
        table.add_row("11", "DNS Recon", "Pengumpulan informasi DNS")
        table.add_row("12", "Email Harvester", "Cari email terkait domain")
        table.add_row("13", "Cloud Detector", "Deteksi layanan cloud")
        table.add_row("14", "CMS Detector", "Identifikasi Content Management System")
        table.add_row("15", "Port Scanner", "Scan port umum")
        table.add_row("0", "Keluar", "Exit program")
        console.print(table)

        choice = console.input("[bold cyan]Pilih nomor menu: [/]").strip()

        if choice == "1":
            target = console.input("[bold green]Masukkan domain: [/]").strip()
            whois_lookup(target)
        elif choice == "2":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            whatweb_scan(target)
        elif choice == "3":
            target = console.input("[bold green]Masukkan IP/domain target: [/]").strip()
            mode = console.input("[bold green]Pilih mode (cepat/lengkap): [/]").strip().lower()
            nmap_scan(target, mode)
        elif choice == "4":
            target = console.input("[bold green]Masukkan domain utama: [/]").strip()
            subdomain_checker(target)
        elif choice == "5":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            gobuster_scan(target)
        elif choice == "6":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            cek_header(target)
        elif choice == "7":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            waf_detection(target)
        elif choice == "8":
            target = console.input("[bold green]Masukkan URL target: [/]").strip()
            screenshot_web(target)
        elif choice == "9":
            username = console.input("[bold green]Masukkan username: [/]").strip()
            userrecon_scan(username)
        elif choice == "10":
            target = console.input("[bold green]Masukkan domain/target: [/]").strip()
            godorker_scan(target)
        elif choice == "11":
            target = console.input("[bold green]Masukkan domain: [/]").strip()
            dns_recon(target)
        elif choice == "12":
            target = console.input("[bold green]Masukkan domain: [/]").strip()
            email_harvester(target)
        elif choice == "13":
            target = console.input("[bold green]Masukkan domain: [/]").strip()
            cloud_detector(target)
        elif choice == "14":
            target = console.input("[bold green]Masukkan URL website: [/]").strip()
            cms_detector(target)
        elif choice == "15":
            target = console.input("[bold green]Masukkan IP/domain: [/]").strip()
            port_scanner(target)
        elif choice == "0":
            console.print(Panel.fit("[bold red]Keluar dari program...", title="Sampai Jumpa", style="red"))
            break
        else:
            console.print(Panel.fit("[bold red]Pilihan gak valid! Coba lagi.", style="red"))
        
        console.input("\n[bold yellow]Tekan Enter untuk lanjut...[/]")

if __name__ == "__main__":
    try:
        # Install dependency
        required_modules = [
            ("rich", "rich"),
            ("requests", "requests"),
            ("dns.resolver", "dnspython"),
            ("googlesearch", "google")
        ]
        for import_name, pypi_name in required_modules:
            if os.system(f"python3 -c 'import {import_name}' > /dev/null 2>&1") != 0:
                console.print(f"[yellow]⏳ Menginstall {pypi_name}...[/yellow]")
                res = os.system(f"pip install -q {pypi_name}")
                if res != 0:
                    # Retry with --break-system-packages
                    os.system(f"pip install -q --break-system-packages {pypi_name}")
        
        menu()
    except KeyboardInterrupt:
        console.print("\n[bold red]Program dihentikan paksa![/bold red]")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
