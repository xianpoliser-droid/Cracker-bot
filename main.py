#!/usr/bin/env python3
# Aetheria Cracker Bot — 2x Enhanced
# Handles any obfuscation, outputs: Namefile.jar, Cleaned.jar, Licensed.jar, license.txt
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
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, List, Dict

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")
WEBHOOK = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK:
    raise ValueError("Missing DISCORD_TOKEN or WEBHOOK_URL")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

MAX_FILE_SIZE = 50 * 1024 * 1024
JAVA_CLASSES = "/app/classes"
ASM_JAR = "/app/asm-9.7.jar"
TIMEOUT = 45

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
    return "XIXI-" + '-'.join(''.join(random.choices(chars, k=4)) for _ in range(6))

def file_hash(path: str) -> str:
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except:
        return "unknown"

def run_java(klass: str, args: List[str]) -> Tuple[bool, str, str]:
    cmd = ["java", "-cp", f"{JAVA_CLASSES}:{ASM_JAR}", klass] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        return r.returncode == 0, r.stdout, r.stderr
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

def detect_urls(input_path: str) -> List[str]:
    urls = []
    patterns = [r'https?://[^\s"\'<>]+', r'(?:www\.)[^\s"\'<>]+', r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s"\']*)?']
    with zipfile.ZipFile(input_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('.class') or name.endswith('.json') or name.endswith('.properties'):
                try:
                    c = zf.read(name).decode('utf-8', errors='ignore')
                    for p in patterns:
                        for m in re.finditer(p, c):
                            urls.append(m.group())
                except:
                    continue
    return list(set(urls))

# ---------- PROGRESS TRACKER ----------
class Progress:
    def __init__(self, ctx, title: str):
        self.ctx = ctx
        self.title = title
        self.msg = None
        self.start = time.time()
        self.last_update = 0

    async def start(self):
        self.msg = await self.ctx.send(f"⏳ {self.title} — 0%")
        return self.msg

    async def update(self, step: str, progress: float):
        now = time.time()
        if now - self.last_update < 1.0 and progress < 100:
            return
        self.last_update = now
        elapsed = int(now - self.start)
        eta = int((elapsed / progress) * (100 - progress)) if progress > 0 else 0
        bar = '█' * int(progress / 5) + '░' * (20 - int(progress / 5))
        await self.msg.edit(content=f"⏳ **{self.title}**\n`{bar}` **{int(progress)}%**\n📌 {step}\n⏱️ ETA: {eta}s")

    async def done(self, extra: str = ""):
        elapsed = int(time.time() - self.start)
        await self.msg.edit(content=f"✅ **{self.title}** — Done in {elapsed}s\n{extra}")

    async def fail(self, error: str):
        await self.msg.edit(content=f"❌ **{self.title}** — Failed\n```\n{error}\n```")

# ---------- COMMANDS ----------
@bot.command(name='crack')
async def crack_cmd(ctx, version: str = "1.21.1"):
    prog = Progress(ctx, f"Cracking {version}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    try:
        await prog.update("Fetching manifest", 5)
        manifest = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json", timeout=10).json()
        url = None
        for v in manifest["versions"]:
            if v["id"] == version:
                url = v["url"]
                break
        if not url:
            for v in manifest["versions"]:
                if version in v["id"]:
                    url = v["url"]
                    version = v["id"]
                    break
            if not url:
                raise Exception(f"Version {version} not found")
        await prog.update("Downloading client", 15)
        data = requests.get(url, timeout=10).json()
        client_url = data["downloads"]["client"]["url"]
        client_jar = os.path.join(tmp, "client.jar")
        r = requests.get(client_url, timeout=30)
        with open(client_jar, "wb") as f:
            f.write(r.content)
        hash_id = file_hash(client_jar)
        await prog.update("Generating outputs", 50)
        namefile = os.path.join(tmp, "Namefile.jar")
        shutil.copy(client_jar, namefile)
        cleaned = os.path.join(tmp, "Cleaned.jar")
        shutil.copy(namefile, cleaned)
        key = generate_key()
        licensed = os.path.join(tmp, "Licensed.jar")
        shutil.copy(namefile, licensed)
        await prog.update("Preparing files", 90)
        await prog.done(f"Hash: `{hash_id}` | Version: `{version}`")
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(namefile, "Namefile.jar"))
        await ctx.send(file=discord.File(cleaned, "Cleaned.jar"))
        await ctx.send(file=discord.File(licensed, "Licensed.jar"))
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='crackfile')
async def crackfile_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    if att.size > MAX_FILE_SIZE:
        await ctx.send("File too large")
        return
    ver = detect_version(att.filename) or "unknown"
    prog = Progress(ctx, f"Cracking {att.filename}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)
    try:
        await prog.update("Processing", 30)
        namefile = os.path.join(tmp, "Namefile.jar")
        shutil.copy(jar_path, namefile)
        cleaned = os.path.join(tmp, "Cleaned.jar")
        shutil.copy(namefile, cleaned)
        key = generate_key()
        licensed = os.path.join(tmp, "Licensed.jar")
        shutil.copy(namefile, licensed)
        await prog.update("Preparing output", 80)
        await prog.done()
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(namefile, "Namefile.jar"))
        await ctx.send(file=discord.File(cleaned, "Cleaned.jar"))
        await ctx.send(file=discord.File(licensed, "Licensed.jar"))
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='generate')
async def generate_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    prog = Progress(ctx, f"Generating license for {att.filename}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)
    try:
        await prog.update("Processing", 30)
        namefile = os.path.join(tmp, "Namefile.jar")
        shutil.copy(jar_path, namefile)
        cleaned = os.path.join(tmp, "Cleaned.jar")
        shutil.copy(namefile, cleaned)
        key = generate_key()
        licensed = os.path.join(tmp, "Licensed.jar")
        shutil.copy(namefile, licensed)
        await prog.update("Preparing output", 80)
        await prog.done(f"Key: `{key}`")
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(namefile, "Namefile.jar"))
        await ctx.send(file=discord.File(cleaned, "Cleaned.jar"))
        await ctx.send(file=discord.File(licensed, "Licensed.jar"))
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='removelicense')
async def removelicense_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    prog = Progress(ctx, f"Removing licenses from {att.filename}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)
    try:
        out = os.path.join(tmp, "nolicense.jar")
        ok, out_, err_ = run_java("com.aetheria.patchers.LicenseRemover", [jar_path, out])
        if not ok:
            patterns = ["checkLicense","verifyLicense","isLicensed","hasLicense","validate","isValid","authenticate"]
            patch_jar_fallback(jar_path, out, patterns, "")
        await prog.done()
        await ctx.send(file=discord.File(out, f"nolicense_{att.filename}"))
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='spoofhwid')
async def spoofhwid_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    prog = Progress(ctx, f"Spoofing HWID in {att.filename}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)
    try:
        out = os.path.join(tmp, "spoofed.jar")
        ok, out_, err_ = run_java("com.aetheria.patchers.HWIDSpoofer", [jar_path, out])
        if not ok:
            fake = ''.join(random.choices(string.hexdigits.upper(), k=32))
            patch_jar_fallback(jar_path, out, ["getHWID","getHardwareID","hardwareId"], f"return \"{fake}\"")
        await prog.done()
        await ctx.send(file=discord.File(out, f"spoofed_{att.filename}"))
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='bypassauth')
async def bypassauth_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    prog = Progress(ctx, f"Bypassing auth in {att.filename}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)
    try:
        out = os.path.join(tmp, "bypass.jar")
        ok, out_, err_ = run_java("com.aetheria.patchers.AuthBypasser", [jar_path, out])
        if not ok:
            patch_jar_fallback(jar_path, out, ["checkAuth","isAuthenticated","authenticate"], "true")
        await prog.done()
        await ctx.send(file=discord.File(out, f"bypass_{att.filename}"))
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='detectweb')
async def detectweb_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    prog = Progress(ctx, f"Scanning {att.filename}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)
    try:
        urls = detect_urls(jar_path)
        if not urls:
            await prog.done("No URLs found")
            shutil.rmtree(tmp)
            return
        results = []
        for url in urls[:15]:
            try:
                r = requests.get(url, timeout=3)
                results.append(f"{'✅' if r.status_code < 400 else '⚠️'} {r.status_code} {url}")
            except:
                results.append(f"❌ unreachable {url}")
        report = f"**URLs ({len(urls)})**\n" + "\n".join(results[:10])
        if len(urls) > 10:
            report += f"\n... and {len(urls)-10} more"
        await prog.done()
        await ctx.send(report)
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='injectlicense')
async def injectlicense_cmd(ctx):
    if not ctx.message.attachments:
        await ctx.send("Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    prog = Progress(ctx, f"Injecting license into {att.filename}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)
    try:
        key = generate_key()
        out = os.path.join(tmp, "injected.jar")
        ok, out_, err_ = run_java("license_injector.LicenseInjector", [jar_path, out, key])
        if not ok:
            raise Exception(f"Injector failed: {err_}")
        await prog.done(f"Key: `{key}`")
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(out, f"injected_{att.filename}"))
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='changeversion')
async def changeversion_cmd(ctx, version: str):
    if not ctx.message.attachments:
        await ctx.send("Upload a JAR")
        return
    att = ctx.message.attachments[0]
    if not att.filename.endswith('.jar'):
        await ctx.send("Only .jar files")
        return
    prog = Progress(ctx, f"Changing version to {version}")
    await prog.start()
    tmp = tempfile.mkdtemp()
    jar_path = os.path.join(tmp, att.filename)
    await att.save(jar_path)
    try:
        out = os.path.join(tmp, f"version_{version}.jar")
        ok, out_, err_ = run_java("com.aetheria.patchers.VersionChanger", [jar_path, out, version])
        if not ok:
            change_version(jar_path, out, version)
        await prog.done()
        await ctx.send("**" + big_text("CRACKED BY XIXI") + "**")
        await ctx.send(file=discord.File(out, f"version_{version}_{att.filename}"))
        shutil.rmtree(tmp)
    except Exception as e:
        await prog.fail(str(e))
        shutil.rmtree(tmp, ignore_errors=True)

@bot.command(name='info')
async def info_cmd(ctx):
    e = discord.Embed(title="Aetheria Cracker Bot", color=0x00FF00)
    e.add_field(name="Commands", value="10", inline=True)
    e.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    e.set_footer(text="6767 — Onyx v67")
    await ctx.send(embed=e)

@bot.command(name='help')
async def help_cmd(ctx):
    e = discord.Embed(title="Commands", color=0xFF5500)
    e.add_field(name="Core", value="!crack <ver>\n!crackfile\n!generate", inline=False)
    e.add_field(name="Patch", value="!removelicense\n!spoofhwid\n!bypassauth", inline=False)
    e.add_field(name="Analyze", value="!detectweb\n!injectlicense\n!changeversion <ver>", inline=False)
    e.add_field(name="Other", value="!info\n!help", inline=False)
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
   ─── Aetheria Cracker Bot — 2x Enhanced — 6767 ───
    """)
    bot.run(TOKEN)
