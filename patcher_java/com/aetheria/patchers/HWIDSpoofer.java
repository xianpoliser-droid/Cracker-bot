package com.aetheria.patchers;

import java.io.*;
import java.util.*;
import java.util.jar.*;

public class HWIDSpoofer {
    private static final String[] PATTERNS = {
        "getHWID", "getHardwareID", "hardwareId",
        "deviceId", "machineId", "fingerprint", "serial"
    };

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("Usage: java HWIDSpoofer <input.jar> <output.jar>");
            System.exit(1);
        }
        String input = args[0];
        String output = args[1];

        String fake = UUID.randomUUID().toString().replace("-", "").substring(0, 32);

        Map<String, byte[]> classes = new LinkedHashMap<>();
        try (JarFile jar = new JarFile(input)) {
            Enumeration<JarEntry> entries = jar.entries();
            while (entries.hasMoreElements()) {
                JarEntry entry = entries.nextElement();
                if (entry.getName().endsWith(".class")) {
                    try (InputStream is = jar.getInputStream(entry)) {
                        classes.put(entry.getName(), is.readAllBytes());
                    }
                }
            }
        }

        int patched = 0;
        for (Map.Entry<String, byte[]> e : classes.entrySet()) {
            byte[] data = e.getValue();
            String content = new String(data, "UTF-8");
            boolean modified = false;
            for (String p : PATTERNS) {
                if (content.contains(p)) {
                    content = content.replace(p, "return \"" + fake + "\"");
                    modified = true;
                }
            }
            if (modified) {
                classes.put(e.getKey(), content.getBytes("UTF-8"));
                patched++;
            }
        }

        try (JarOutputStream jos = new JarOutputStream(new FileOutputStream(output))) {
            for (Map.Entry<String, byte[]> e : classes.entrySet()) {
                jos.putNextEntry(new JarEntry(e.getKey()));
                jos.write(e.getValue());
                jos.closeEntry();
            }
        }
        System.out.println("Spoofed " + patched + " classes");
    }
}
