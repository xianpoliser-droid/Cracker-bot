#!/usr/bin/env python3
# Cracker Bot — Full Production
# 9 commands: CrackClient, generate, removelicensehwid, malwarecheck, checkdirectory, changeversion, patchpanel, decompile, info
# 6767

import os
import sys
import json
import time
import zipfile
import shutil
import tempfile
import subprocess
import requests
import discord
from discord.ext import commands
import random
import string
import re
import hashlib
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "?")
WEBHOOK = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK:
    raise ValueError("Missing environment variables")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

MAX_FILE_SIZE = 100 * 1024 * 1024
executor = ThreadPoolExecutor(max_workers=4)

# ---------- UTILITIES ----------
def big_text(text: str) -> str:
    m = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘',
        'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝',
        'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢',
        'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧',
        'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬',
        'Z': '𝗭', ' ': ' ', '\n': '\n'
    }
    return ''.join(m.get(c, c) for c in text)

def detect_version(filename: str) -> Optional[str]:
    for p in [r'(\d+\.\d+\.\d+)', r'(\d+\.\d+)', r'(\d+\.\d+\.\d+\.\d+)']:
        m = re.search(p, filename)
        if m:
            return m.group(1)
    return None

def generate_key() -> str:
    chars = string.ascii_uppercase + string.digits
    return '-'.join(''.join(random.choices(chars, k=4)) for _ in range(4))

def file_hash(path: str) -> str:
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except:
        return "unknown"

def patch_jar(input_path: str, output_path: str, patterns: List[str], replacement: str = "") -> Tuple[int, int]:
    patched = 0
    total = 0
    with zipfile.ZipFile(input_path, 'r') as zf:
        names = zf.namelist()
        total = len(names)
        with zipfile.ZipFile(output_path, 'w') as out:
            for name in names:
                data = zf.read(name)
                if name.endswith('.class'):
                    orig = data
                    for p in patterns:
                        if isinstance(p, bytes):
                            data = data.replace(p, replacement.encode() if replacement else b'')
                        else:
                            data = data.replace(p.encode(), replacement.encode() if replacement else b'')
                    if data != orig:
                        patched += 1
                out.writestr(name, data)
    return patched, total

def change_version(input_path: str, output_path: str, new_version: str) -> bool:
    modified = False
    with zipfile.ZipFile(input_path, 'r') as zf:
        with zipfile.ZipFile(output_path, 'w') as out:
            for name in zf.namelist():
                data = zf.read(name)
                if name in ('fabric.mod.json', 'fabric-mod.json'):
                    try:
                        c = data.decode('utf-8', errors='ignore')
                        c = re.sub(r'"version"\s*:\s*"[^"]+"', f'"version":"{new_version}"', c)
                        data = c.encode('utf-8')
                        modified = True
                    except:
                        pass
                elif name == 'version.json':
                    try:
                        c = data.decode('utf-8', errors='ignore')
                        c = re.sub(r'"id"\s*:\s*"[^"]+"', f'"id":"{new_version}"', c)
                        data = c.encode('utf-8')
                        modified = True
                    except:
                        pass
                elif name == 'META-INF/MANIFEST.MF':
                    try:
                        c = data.decode('utf-8', errors='ignore')
                        c = re.sub(r'Implementation-Version:\s*.+', f'Implementation-Version: {new_version}', c)
                        data = c.encode('utf-8')
                        modified = True
                    except:
                        pass
                out.writestr(name, data)
    return modified

def extract_source(input_path: str, output_path: str) -> bool:
    try:
        with zipfile.ZipFile(input_path, 'r') as zf:
            with zipfile.ZipFile(output_path, 'w') as out:
                for name in zf.namelist():
                    if name.endswith('.java'):
                        out.writestr(name, zf.read(name))
        return True
    except:
        return False

def decompile_full(input_jar: str, output_dir: str) -> bool:
    cfr_path = "/tmp/cfr.jar"
    if not os.path.exists(cfr_path):
        try:
            r = requests.get("https://github.com/leibnitz27/cfr/releases/download/0.152/cfr-0.152.jar", timeout=30)
            with open(cfr_path, 'wb') as f:
                f.write(r.content)
        except:
            return False

    cmd = ["java", "-jar", cfr_path, input_jar, "--outputdir", output_dir, "--silent", "true"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return True
    except:
        return False

# ---------- MALWARE PATTERNS ----------
MALWARE_PATTERNS = {
    "discord_webhook": r'https?://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+',
    "token": r'[a-zA-Z0-9_-]{24,28}\.[a-zA-Z0-9_-]{6,7}\.[a-zA-Z0-9_-]{27,38}',
    "ip_logger": r'(?:\d{1,3}\.){3}\d{1,3}:[0-9]{1,5}|http[s]?://(?:[\w-]+\.)+[\w-]+/[\w./?%&=]*(?:log|logger|ip)',
    "telegram_bot": r'https?://api\.telegram\.org/bot\d+:[A-Za-z0-9_-]+',
    "system_calls": r'(Runtime\.exec|ProcessBuilder|getRuntime\(\)\.exec)',
    "reflection": r'(\.getDeclaredMethod|\.setAccessible|\.invoke)',
    "file_operations": r'(Files\.write|FileOutputStream|FileWriter|RandomAccessFile)',
    "network": r'(Socket|URL|HttpURLConnection|URLConnection|DatagramSocket)',
    "rat": r'(RAT|Remote Access Trojan|backdoor|shellcode)',
    "beacon": r'(C2|command.control|callback|beacon)',
}

def scan_malware(jar_path: str) -> Dict[str, List[str]]:
    results = {}
    for category in MALWARE_PATTERNS:
        results[category] = []
    with zipfile.ZipFile(jar_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('.class') or name.endswith('.json') or name.endswith('.properties'):
                try:
                    content = zf.read(name).decode('utf-8', errors='ignore')
                    for category, pattern in MALWARE_PATTERNS.items():
                        for match in re.finditer(pattern, content, re.IGNORECASE):
                            results[category].append(f"{name} → {match.group()}")
                except:
                    continue
    return results

def get_directory_structure(jar_path: str) -> str:
    structure = []
    with zipfile.ZipFile(jar_path, 'r') as zf:
        for name in sorted(zf.namelist()):
            structure.append(name)
    return "\n".join(structure[:50]) + ("\n... and more" if len(structure) > 50 else "")

def inject_license_key(input_path: str, output_path: str, license_key: str) -> bool:
    shutil.copy(input_path, output_path)
    with zipfile.ZipFile(output_path, 'a') as zf:
        zf.writestr("license.txt", f"LICENSE_KEY={license_key}\nGENERATED={time.ctime()}\n")
    return True

def find_main_class(jar_path: str) -> Optional[str]:
    try:
        with zipfile.ZipFile(jar_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.class') and ('Main' in name or 'Client' in name or 'Launcher' in name):
                    return name
    except:
        pass
    return None

def patch_source_files(src_dir: str, old_url: str, new_url: str) -> int:
    patched = 0
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.java'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', errors='ignore') as f:
                        content = f.read()
                    if old_url in content or old_url.replace('https://', '').replace('http://', '') in content:
                        content = content.replace(old_url, new_url)
                        content = content.replace(old_url.replace('https://', ''), new_url.replace('http://', ''))
                        with open(path, 'w') as f:
                            f.write(content)
                        patched += 1
                except:
                    continue
    return patched

def recompile_source(src_dir: str, output_jar: str) -> bool:
    java_files = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.java'):
                java_files.append(os.path.join(root, file))

    if not java_files:
        return False

    class_dir = os.path.join(src_dir, "classes")
    os.makedirs(class_dir, exist_ok=True)

    cmd = ["javac", "-d", class_dir, "-cp", "."] + java_files
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except:
        return False

    with zipfile.ZipFile(output_jar, 'w') as zf:
        for root, dirs, files in os.walk(class_dir):
            for file in files:
                path = os.path.join(root, file)
                arcname = os.path.relpath(path, class_dir)
                zf.write(path, arcname)

    return True

# ---------- COMMANDS ----------

@bot.command(name='CrackClient')
async def crackclient_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    base, ext = os.path.splitext(att.filename)
    await ctx.send(f"Cracking {att.filename}...")
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        patterns = [
            "checkLicense","verifyLicense","isLicensed","hasLicense",
            "validate","isValid","authenticate","isAuthenticated",
            "licenseKey","getLicense","verifyKey","checkKey",
            "isPremium","hasPremium","checkPremium","premium",
            "isCracked","hasCrack","checkCrack","cracked",
            "HWID","getHWID","getHardwareID","hardwareId",
            "deviceId","machineId","fingerprint","serial"
        ]
        namefile = os.path.join(tmp, f"{base}.jar")
        shutil.copy(jar_path, namefile)

        cracked = os.path.join(tmp, f"{base}X.jar")
        patch_jar(jar_path, cracked, patterns, "")

        source_zip = os.path.join(tmp, f"{base}.zip")
        extract_source(jar_path, source_zip)

        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(namefile, f"{base}.jar"))
        await ctx.send(file=discord.File(cracked, f"{base}X.jar"))
        await ctx.send(file=discord.File(source_zip, f"{base}.zip"))

        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='generate')
async def generate_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    base, ext = os.path.splitext(att.filename)
    await ctx.send(f"Generating license for {att.filename}...")
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        key = generate_key()
        licensed = os.path.join(tmp, f"{base}L.jar")
        inject_license_key(jar_path, licensed, key)

        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(licensed, f"{base}L.jar"))
        await ctx.send(f"||License Key: `{key}`||")

        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='removelicensehwid')
async def removelicensehwid_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    base, ext = os.path.splitext(att.filename)
    await ctx.send(f"Removing license/HWID from {att.filename}...")
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        patterns = [
            "checkLicense","verifyLicense","isLicensed","hasLicense",
            "validate","isValid","authenticate","isAuthenticated",
            "licenseKey","getLicense","verifyKey","checkKey",
            "isPremium","hasPremium","checkPremium","premium",
            "isCracked","hasCrack","checkCrack","cracked",
            "HWID","getHWID","getHardwareID","hardwareId",
            "deviceId","machineId","fingerprint","serial"
        ]
        out = os.path.join(tmp, f"{base}_clean.jar")
        patch_jar(jar_path, out, patterns, "")

        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(out, f"{base}_clean.jar"))

        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='malwarecheck')
async def malwarecheck_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    await ctx.send(f"Scanning {att.filename} for malware...")
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        results = scan_malware(jar_path)
        found = False
        report = f"**Malware Scan Report for {att.filename}**\n"
        for category, matches in results.items():
            if matches:
                found = True
                report += f"\n**{category.upper()} DETECTED:**\n"
                for m in matches[:5]:
                    report += f"  {m}\n"
                if len(matches) > 5:
                    report += f"  ... and {len(matches)-5} more\n"

        if not found:
            report += "\n✅ No malware detected."

        await ctx.send(report)
        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='checkdirectory')
async def checkdirectory_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    await ctx.send(f"Getting directory structure of {att.filename}...")
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        structure = get_directory_structure(jar_path)
        if len(structure) > 1900:
            chunks = [structure[i:i+1900] for i in range(0, len(structure), 1900)]
            for chunk in chunks:
                await ctx.send(f"```\n{chunk}\n```")
        else:
            await ctx.send(f"```\n{structure}\n```")
        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='changeversion')
async def changeversion_cmd(ctx, version: str):
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    base, ext = os.path.splitext(att.filename)
    await ctx.send(f"Changing version to {version}...")
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        out = os.path.join(tmp, f"{base}_{version}.jar")
        change_version(jar_path, out, version)
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(out, f"{base}_{version}.jar"))
        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='patchpanel')
async def patchpanel_cmd(ctx, panel_url: str = None):
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    if not panel_url:
        await ctx.send("Specify the panel URL to replace (e.g., ?patchpanel https://ownerpanel.com)")
        return

    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    base, ext = os.path.splitext(att.filename)
    await ctx.send(f"Patching panel URL in {att.filename}...\nDecompiling, replacing URL, recompiling... (may take 2-5 min)")

    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        src_dir = os.path.join(tmp, "src")
        os.makedirs(src_dir, exist_ok=True)
        await ctx.send("Step 1/3: Decompiling...")
        if not decompile_full(jar_path, src_dir):
            await ctx.send("Decompilation failed.")
            shutil.rmtree(tmp)
            return

        await ctx.send("Step 2/3: Replacing panel URL...")
        new_url = "http://127.0.0.1/license"
        patched = patch_source_files(src_dir, panel_url, new_url)
        if patched == 0:
            patterns = ["checkLicense","verifyLicense","isLicensed","hasLicense","authenticate","isAuthenticated","validate","isValid"]
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    if file.endswith('.java'):
                        path = os.path.join(root, file)
                        try:
                            with open(path, 'r', errors='ignore') as f:
                                content = f.read()
                            modified = False
                            for p in patterns:
                                if p in content:
                                    content = content.replace(p, "true")
                                    modified = True
                            if modified:
                                with open(path, 'w') as f:
                                    f.write(content)
                                patched += 1
                        except:
                            continue

        await ctx.send(f"Patched {patched} files.")

        await ctx.send("Step 3/3: Recompiling...")
        output_jar = os.path.join(tmp, f"{base}_patched.jar")
        if not recompile_source(src_dir, output_jar):
            await ctx.send("Recompilation failed.")
            shutil.rmtree(tmp)
            return

        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(output_jar, f"{base}_patched.jar"))
        await ctx.send(f"✅ Panel URL replaced: `{panel_url}` → `{new_url}`")

        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

# ---------- NEW COMMANDS: decompile + info ----------

@bot.command(name='decompile')
async def decompile_cmd(ctx):
    """?decompile <attachment> — Extract full source code from JAR"""
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    await ctx.send(f"Decompiling {att.filename}... (this may take 2-5 min)")

    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        src_dir = os.path.join(tmp, "src")
        os.makedirs(src_dir, exist_ok=True)

        if not decompile_full(jar_path, src_dir):
            await ctx.send("Decompilation failed. The client may be heavily obfuscated.")
            shutil.rmtree(tmp)
            return

        # Create zip of all source files
        base, ext = os.path.splitext(att.filename)
        source_zip = os.path.join(tmp, f"{base}_source.zip")
        with zipfile.ZipFile(source_zip, 'w') as zf:
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    path = os.path.join(root, file)
                    arcname = os.path.relpath(path, src_dir)
                    zf.write(path, arcname)

        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(source_zip, f"{base}_source.zip"))
        await ctx.send(f"✅ Full source extracted. {len(os.listdir(src_dir))} files.")

        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='info')
async def info_cmd(ctx):
    """?info <attachment> — Deep client analysis"""
    if not ctx.message.attachments:
        await ctx.send("Upload a client JAR with the command")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send(f"File too large (max {MAX_FILE_SIZE//(1024*1024)}MB)")
        return

    await ctx.send(f"Analyzing {att.filename}...")

    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)

    try:
        info = {
            "name": att.filename,
            "size": f"{att.size // 1024} KB",
            "version": detect_version(att.filename) or "unknown",
            "main_class": find_main_class(jar_path) or "not found",
            "files": 0,
            "classes": 0,
            "urls": [],
            "panel_domains": [],
            "suspicious": []
        }

        with zipfile.ZipFile(jar_path, 'r') as zf:
            info["files"] = len(zf.namelist())
            for name in zf.namelist():
                if name.endswith('.class'):
                    info["classes"] += 1
                if name.endswith('.class') or name.endswith('.json') or name.endswith('.properties'):
                    try:
                        content = zf.read(name).decode('utf-8', errors='ignore')
                        # Find URLs
                        urls = re.findall(r'https?://[^\s"\'<>]+', content)
                        for url in urls:
                            if url not in info["urls"]:
                                info["urls"].append(url)
                                if "panel" in url or "license" in url or "auth" in url or "api" in url:
                                    info["panel_domains"].append(url)
                        # Suspicious methods
                        suspicious_methods = [
                            "Runtime.exec", "ProcessBuilder", "getDeclaredMethod",
                            "setAccessible", "invoke", "webhook", "discord.com",
                            "telegram", "bot", "logger", "rat", "backdoor"
                        ]
                        for sm in suspicious_methods:
                            if sm in content:
                                if sm not in info["suspicious"]:
                                    info["suspicious"].append(sm)
                    except:
                        continue

        embed = discord.Embed(title=f"Client Analysis: {info['name']}", color=0x00AAFF)
        embed.add_field(name="Version", value=info["version"], inline=True)
        embed.add_field(name="Size", value=info["size"], inline=True)
        embed.add_field(name="Main Class", value=info["main_class"], inline=True)
        embed.add_field(name="Total Files", value=str(info["files"]), inline=True)
        embed.add_field(name="Classes", value=str(info["classes"]), inline=True)
        embed.add_field(name="URLs Found", value=str(len(info["urls"])), inline=True)

        if info["panel_domains"]:
            embed.add_field(name="Panel/License Domains", value="\n".join(info["panel_domains"][:5]), inline=False)
        if info["suspicious"]:
            embed.add_field(name="Suspicious Methods", value=", ".join(info["suspicious"][:10]), inline=False)

        embed.set_footer(text="6767 — Onyx v67")
        await ctx.send(embed=embed)

        shutil.rmtree(tmp)
    except Exception as e:
        await ctx.send(f"Failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='help')
async def help_cmd(ctx):
    e = discord.Embed(title="Cracker Bot — 9 Commands", color=0xFF5500)
    e.add_field(name="?CrackClient", value="Crack client → 3 files", inline=False)
    e.add_field(name="?generate", value="Generate license key", inline=False)
    e.add_field(name="?removelicensehwid", value="Remove license/HWID checks", inline=False)
    e.add_field(name="?malwarecheck", value="Scan for malware", inline=False)
    e.add_field(name="?checkdirectory", value="Show directory structure", inline=False)
    e.add_field(name="?changeversion <ver>", value="Change client version", inline=False)
    e.add_field(name="?patchpanel <panel_url>", value="Decompile → replace panel URL → recompile", inline=False)
    e.add_field(name="?decompile", value="Extract full source code", inline=False)
    e.add_field(name="?info", value="Deep client analysis", inline=False)
    e.set_footer(text="6767 — Onyx v67")
    await ctx.send(embed=e)

@bot.event
async def on_ready():
    print(f"Ready: {bot.user}")
    print(f"Servers: {len(bot.guilds)}")

if __name__ == "__main__":
    print("""
   ██████╗██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗
  ██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
  ██║     ██████╔╝███████║██║     █████╔╝ █████╗  ██████╔╝
  ██║     ██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
  ╚██████╗██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║
   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
   ─── Cracker Bot — 9 Commands — 6767 ───
    """)
    bot.run(TOKEN)
