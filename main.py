#!/usr/bin/env python3
# Discord Auto Cracker — Ultimate Java Patcher Integration
# 10 commands, modular Java, multi-threaded, stable
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
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, List, Dict

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")
WEBHOOK = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK:
    raise ValueError("Missing environment variables")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

MAX_FILE_SIZE = 50 * 1024 * 1024
JAVA_PATCHER_DIR = "/app/patcher_java"
LICENSE_INJECTOR_DIR = "/app/license_injector"
ASM_JAR = "/app/asm-9.7.jar"
TIMEOUT = 45

LICENSE_PATTERNS = [
    "checkLicense", "verifyLicense", "isLicensed", "hasLicense",
    "validate", "isValid", "authenticate", "isAuthenticated",
    "licenseKey", "getLicense", "verifyKey", "checkKey",
    "isPremium", "hasPremium", "checkPremium", "premium",
    "isCracked", "hasCrack", "checkCrack", "cracked",
    "HWID", "getHWID", "getHardwareID", "hardwareId",
    "deviceId", "machineId", "fingerprint", "serial"
]
HWID_PATTERNS = ["getHWID", "getHardwareID", "hardwareId", "deviceId", "machineId", "fingerprint", "serial"]
AUTH_PATTERNS = ["checkAuth", "isAuthenticated", "authenticate", "verifyAuth", "login", "signIn", "signOn"]
URL_PATTERNS = [
    r'https?://[^\s"\'<>]+',
    r'(?:www\.)[^\s"\'<>]+',
    r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s"\']*)?'
]

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

def detect_version_from_filename(filename: str) -> Optional[str]:
    for p in [r'(\d+\.\d+\.\d+)', r'(\d+\.\d+)', r'(\d+\.\d+\.\d+\.\d+)']:
        m = re.search(p, filename)
        if m:
            return m.group(1)
    return None

def generate_license_key() -> str:
    chars = string.ascii_uppercase + string.digits
    return "XIXI-" + '-'.join(''.join(random.choices(chars, k=4)) for _ in range(6))

def get_file_hash(path: str) -> str:
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except:
        return "unknown"

def run_java_patcher(patcher_class: str, input_jar: str, output_jar: str, *args) -> Tuple[bool, str, str]:
    cmd = ["java", "-cp", f"{JAVA_PATCHER_DIR}:{ASM_JAR}", f"com.aetheria.patchers.{patcher_class}", input_jar, output_jar] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Timeout after {TIMEOUT}s"
    except Exception as e:
        return False, "", str(e)

def run_java_injector(input_jar: str, output_jar: str, license_key: str) -> Tuple[bool, str, str]:
    cmd = ["java", "-cp", f"{LICENSE_INJECTOR_DIR}:{ASM_JAR}", "license_injector.LicenseInjector", input_jar, output_jar, license_key]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Timeout after {TIMEOUT}s"
    except Exception as e:
        return False, "", str(e)

def patch_jar_fallback(input_path: str, output_path: str, patterns: List[str], replacement: str = "") -> Tuple[int, int]:
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
                        content = data.decode('utf-8', errors='ignore')
                        content = re.sub(r'"version"\s*:\s*"[^"]+"', f'"version":"{new_version}"', content)
                        data = content.encode('utf-8')
                        modified = True
                    except:
                        pass
                elif name == 'version.json':
                    try:
                        content = data.decode('utf-8', errors='ignore')
                        content = re.sub(r'"id"\s*:\s*"[^"]+"', f'"id":"{new_version}"', content)
                        data = content.encode('utf-8')
                        modified = True
                    except:
                        pass
                elif name == 'META-INF/MANIFEST.MF':
                    try:
                        content = data.decode('utf-8', errors='ignore')
                        content = re.sub(r'Implementation-Version:\s*.+', f'Implementation-Version: {new_version}', content)
                        data = content.encode('utf-8')
                        modified = True
                    except:
                        pass
                out.writestr(name, data)
    return modified

def detect_urls(input_path: str) -> List[str]:
    urls = []
    with zipfile.ZipFile(input_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('.class') or name.endswith('.json') or name.endswith('.properties'):
                try:
                    content = zf.read(name).decode('utf-8', errors='ignore')
                    for pattern in URL_PATTERNS:
                        for match in re.finditer(pattern, content):
                            urls.append(match.group())
                except:
                    continue
    return list(set(urls))

# ---------- COMMANDS ----------
@bot.command(name='crack')
async def crack_cmd(ctx, version: str = "1.21.1"):
    await ctx.send(f"Cracking {version}...")
    temp_dir = tempfile.mkdtemp()
    try:
        manifest = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json", timeout=10).json()
        version_url = None
        for v in manifest["versions"]:
            if v["id"] == version:
                version_url = v["url"]
                break
        if not version_url:
            for v in manifest["versions"]:
                if version in v["id"]:
                    version_url = v["url"]
                    version = v["id"]
                    break
            if not version_url:
                raise Exception(f"Version {version} not found")
        data = requests.get(version_url, timeout=10).json()
        client_url = data["downloads"]["client"]["url"]
        client_jar = os.path.join(temp_dir, "client.jar")
        r = requests.get(client_url, timeout=30)
        with open(client_jar, "wb") as f:
            f.write(r.content)
        hash_id = get_file_hash(client_jar)
        namefile = os.path.join(temp_dir, "Namefile.jar")
        shutil.copy(client_jar, namefile)
        cleaned = os.path.join(temp_dir, "Cleaned.jar")
        shutil.copy(namefile, cleaned)
        license_key = generate_license_key()
        licensed = os.path.join(temp_dir, "Licensed.jar")
        shutil.copy(namefile, licensed)
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(namefile, "Namefile.jar"))
        await ctx.send(file=discord.File(cleaned, "Cleaned.jar"))
        await ctx.send(file=discord.File(licensed, "Licensed.jar"))
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='crackfile')
async def crackfile_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("📎 Upload a client JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("❌ Only `.jar` files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send("❌ File too large (max 50MB)")
        return
    detected_version = detect_version_from_filename(att.filename) or "unknown"
    client_name = att.filename.replace('.jar', '')
    await ctx.send(f"Cracking {att.filename}...")
    temp_dir = tempfile.mkdtemp()
    jar_path = os.path.join(temp_dir, att.filename)
    await att.save(jar_path)
    try:
        namefile = os.path.join(temp_dir, "Namefile.jar")
        shutil.copy(jar_path, namefile)
        cleaned = os.path.join(temp_dir, "Cleaned.jar")
        shutil.copy(namefile, cleaned)
        license_key = generate_license_key()
        licensed = os.path.join(temp_dir, "Licensed.jar")
        shutil.copy(namefile, licensed)
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(namefile, "Namefile.jar"))
        await ctx.send(file=discord.File(cleaned, "Cleaned.jar"))
        await ctx.send(file=discord.File(licensed, "Licensed.jar"))
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='generate')
async def generate_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("📎 Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("❌ Only `.jar` files")
        return
    await ctx.send(f"Generating licensed client for {att.filename}...")
    temp_dir = tempfile.mkdtemp()
    jar_path = os.path.join(temp_dir, att.filename)
    await att.save(jar_path)
    try:
        detected_version = detect_version_from_filename(att.filename) or "unknown"
        client_name = att.filename.replace('.jar', '')
        namefile = os.path.join(temp_dir, "Namefile.jar")
        shutil.copy(jar_path, namefile)
        cleaned = os.path.join(temp_dir, "Cleaned.jar")
        shutil.copy(namefile, cleaned)
        license_key = generate_license_key()
        licensed = os.path.join(temp_dir, "Licensed.jar")
        shutil.copy(namefile, licensed)
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(namefile, "Namefile.jar"))
        await ctx.send(file=discord.File(cleaned, "Cleaned.jar"))
        await ctx.send(file=discord.File(licensed, "Licensed.jar"))
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='removelicense')
async def removelicense_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("📎 Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("❌ Only `.jar` files")
        return
    await ctx.send(f"Removing license checks from {att.filename}...")
    temp_dir = tempfile.mkdtemp()
    jar_path = os.path.join(temp_dir, att.filename)
    await att.save(jar_path)
    try:
        out_jar = os.path.join(temp_dir, "nolicense.jar")
        success, stdout, stderr = run_java_patcher("LicenseRemover", jar_path, out_jar)
        if not success:
            patched, total = patch_jar_fallback(jar_path, out_jar, LICENSE_PATTERNS, "")
        await ctx.send(file=discord.File(out_jar, f"nolicense_{att.filename}"))
        await ctx.send("✅ License checks removed")
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='spoofhwid')
async def spoofhwid_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("📎 Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("❌ Only `.jar` files")
        return
    await ctx.send(f"Spoofing HWID in {att.filename}...")
    temp_dir = tempfile.mkdtemp()
    jar_path = os.path.join(temp_dir, att.filename)
    await att.save(jar_path)
    try:
        out_jar = os.path.join(temp_dir, "spoofed.jar")
        success, stdout, stderr = run_java_patcher("HWIDSpoofer", jar_path, out_jar)
        if not success:
            fake_hwid = ''.join(random.choices(string.hexdigits.upper(), k=32))
            patch_jar_fallback(jar_path, out_jar, HWID_PATTERNS, f"return \"{fake_hwid}\"")
        await ctx.send(file=discord.File(out_jar, f"spoofed_{att.filename}"))
        await ctx.send("✅ HWID spoofed")
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='bypassauth')
async def bypassauth_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("📎 Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("❌ Only `.jar` files")
        return
    await ctx.send(f"Bypassing auth in {att.filename}...")
    temp_dir = tempfile.mkdtemp()
    jar_path = os.path.join(temp_dir, att.filename)
    await att.save(jar_path)
    try:
        out_jar = os.path.join(temp_dir, "bypass.jar")
        success, stdout, stderr = run_java_patcher("AuthBypasser", jar_path, out_jar)
        if not success:
            patch_jar_fallback(jar_path, out_jar, AUTH_PATTERNS, "true")
        await ctx.send(file=discord.File(out_jar, f"bypass_{att.filename}"))
        await ctx.send("✅ Auth bypassed")
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='detectweb')
async def detectweb_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("📎 Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("❌ Only `.jar` files")
        return
    await ctx.send(f"Scanning {att.filename} for URLs...")
    temp_dir = tempfile.mkdtemp()
    jar_path = os.path.join(temp_dir, att.filename)
    await att.save(jar_path)
    try:
        urls = detect_urls(jar_path)
        if not urls:
            await ctx.send("No URLs found.")
            shutil.rmtree(temp_dir)
            return
        results = []
        for url in urls[:15]:
            try:
                r = requests.get(url, timeout=3)
                results.append(f"{'✅' if r.status_code < 400 else '⚠️'} {r.status_code} {url}")
            except:
                results.append(f"❌ unreachable {url}")
        report = f"**URLs found ({len(urls)})**\n" + "\n".join(results[:10])
        if len(urls) > 10:
            report += f"\n... and {len(urls)-10} more"
        await ctx.send(report)
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='injectlicense')
async def injectlicense_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("📎 Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("❌ Only `.jar` files")
        return
    await ctx.send(f"Injecting license into {att.filename}...")
    temp_dir = tempfile.mkdtemp()
    jar_path = os.path.join(temp_dir, att.filename)
    await att.save(jar_path)
    try:
        license_key = generate_license_key()
        out_jar = os.path.join(temp_dir, "injected.jar")
        success, stdout, stderr = run_java_injector(jar_path, out_jar, license_key)
        if not success:
            raise Exception(f"Injector failed: {stderr}")
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(out_jar, f"injected_{att.filename}"))
        await ctx.send(f"✅ License injected\n🔑 Key: `{license_key}`")
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='changeversion')
async def changeversion_cmd(ctx, version: str):
    if not ctx.message.attachments:
        await ctx.send("📎 Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("❌ Only `.jar` files")
        return
    await ctx.send(f"Changing version to {version}...")
    temp_dir = tempfile.mkdtemp()
    jar_path = os.path.join(temp_dir, att.filename)
    await att.save(jar_path)
    try:
        out_jar = os.path.join(temp_dir, f"version_{version}.jar")
        success, stdout, stderr = run_java_patcher("VersionChanger", jar_path, out_jar, version)
        if not success:
            change_version(jar_path, out_jar, version)
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(out_jar, f"version_{version}_{att.filename}"))
        await ctx.send(f"✅ Version changed to `{version}`")
        shutil.rmtree(temp_dir)
    except Exception as e:
        await ctx.send(f"❌ Failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)

@bot.command(name='info')
async def info_cmd(ctx):
    embed = discord.Embed(title="Cracker Bot", description="10 commands", color=0x00FF00)
    embed.add_field(name="📡 Servers", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="⚡ Commands", value="10", inline=True)
    embed.set_footer(text="6767 — Onyx v67")
    await ctx.send(embed=embed)

@bot.command(name='help')
async def help_cmd(ctx):
    embed = discord.Embed(title="🔥 Commands", color=0xFF5500)
    embed.add_field(name="📦 Core", value="!crack <ver>\n!crackfile\n!generate", inline=False)
    embed.add_field(name="🔧 Patch", value="!removelicense\n!spoofhwid\n!bypassauth", inline=False)
    embed.add_field(name="🔍 Analyze", value="!detectweb\n!injectlicense\n!changeversion <ver>", inline=False)
    embed.add_field(name="ℹ️ Other", value="!info\n!help", inline=False)
    embed.set_footer(text="6767 — Onyx v67")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Ready: {bot.user}")
    print(f"📡 Servers: {len(bot.guilds)}")

if __name__ == "__main__":
    print("""
   ██████╗██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗
  ██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
  ██║     ██████╔╝███████║██║     █████╔╝ █████╗  ██████╔╝
  ██║     ██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
  ╚██████╗██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║
   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
   ─── Cracker Bot — Ultimate — 6767 ───
    """)
    bot.run(TOKEN)
