#!/usr/bin/env bash

# Banner
echo -e "\e[1;32m=================================================="
echo -e "       AsepRecon & AsepScan Installer 2026       "
echo -e "==================================================\e[0m"

# Detect environment
if [ -d "/data/data/com.termux/files/usr/bin" ]; then
    ENV="termux"
    echo -e "[*] Lingkungan terdeteksi: \e[1;36mTermux (Android)\e[0m"
else
    ENV="linux"
    echo -e "[*] Lingkungan terdeteksi: \e[1;36mLinux (PC/VirtualBox)\e[0m"
fi

# 1. Update package manager & install system dependencies
if [ "$ENV" = "termux" ]; then
    echo -e "\e[1;33m[*] Melakukan pkg update & upgrade...\e[0m"
    pkg update -y && pkg upgrade -y
    
    echo -e "\e[1;33m[*] Menginstall alat sistem di Termux...\e[0m"
    pkg install -y git python nmap whois whatweb hydra tcpdump golang termux-api
else
    # Detect Linux distro package manager
    if command -v apt &> /dev/null; then
        echo -e "\e[1;33m[*] Melakukan apt update...\e[0m"
        sudo apt update -y
        echo -e "\e[1;33m[*] Menginstall alat sistem via apt...\e[0m"
        sudo apt install -y git python3 python3-pip nmap whois whatweb hydra tcpdump golang
    elif command -v pacman &> /dev/null; then
        echo -e "\e[1;33m[*] Melakukan pacman update...\e[0m"
        sudo pacman -Syu --noconfirm
        echo -e "\e[1;33m[*] Menginstall alat sistem via pacman...\e[0m"
        sudo pacman -S --noconfirm git python python-pip nmap whois hydra tcpdump go
    elif command -v dnf &> /dev/null; then
        echo -e "\e[1;33m[*] Melakukan dnf update...\e[0m"
        sudo dnf update -y
        echo -e "\e[1;33m[*] Menginstall alat sistem via dnf...\e[0m"
        sudo dnf install -y git python3 python3-pip nmap whois hydra tcpdump golang
    else
        echo -e "\e[1;31m[!] Package manager tidak didukung otomatis. Silakan install git, python3, nmap, whois, hydra, tcpdump, dan golang secara manual.\e[0m"
    fi
fi

# 2. Install python packages
echo -e "\e[1;33m[*] Menginstall dependensi Python...\e[0m"
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    PIP_CMD=""
fi

if [ -n "$PIP_CMD" ]; then
    # Cek apakah butuh --break-system-packages (PEP 668)
    if $PIP_CMD install --help 2>&1 | grep -q "break-system-packages"; then
        $PIP_CMD install --user --break-system-packages -r requirements.txt
    else
        $PIP_CMD install --user -r requirements.txt
    fi
else
    echo -e "\e[1;31m[!] Pip tidak ditemukan. Gagal menginstall dependensi Python otomatis.\e[0m"
fi

# 3. Add ~/go/bin to path if using bash
GO_BIN="$HOME/go/bin"
if [ -d "$GO_BIN" ]; then
    if ! grep -q "go/bin" "$HOME/.bashrc" 2>/dev/null; then
        echo 'export PATH="$PATH:$HOME/go/bin"' >> "$HOME/.bashrc"
        echo -e "[*] Menambahkan $GO_BIN ke ~/.bashrc"
    fi
fi

echo -e "\e[1;32m=================================================="
echo -e "         Instalasi Selesai dengan Sukses!        "
echo -e "=================================================="
echo -e "Silakan jalankan script:"
echo -e "  - Termux: python aseprec.py"
echo -e "  - Linux : python3 run.py"
echo -e "==================================================\e[0m"
