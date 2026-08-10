package com.aetheria.patchers;

import java.io.*;
import java.util.*;
import java.util.jar.*;
import java.util.regex.*;

public class VersionChanger {
    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.err.println("Usage: java VersionChanger <input.jar> <output.jar> <new_version>");
            System.exit(1);
        }
        String input = args[0];
        String output = args[1];
        String newVersion = args[2];

        Map<String, byte[]> entries = new LinkedHashMap<>();
        try (JarFile jar = new JarFile(input)) {
            Enumeration<JarEntry> en = jar.entries();
            while (en.hasMoreElements()) {
                JarEntry entry = en.nextElement();
                byte[] data = jar.getInputStream(entry).readAllBytes();
                entries.put(entry.getName(), data);
            }
        }

        int modified = 0;
        for (Map.Entry<String, byte[]> e : entries.entrySet()) {
            String name = e.getKey();
            byte[] data = e.getValue();
            if (name.equals("fabric.mod.json") || name.equals("fabric-mod.json")) {
                try {
                    String content = new String(data, "UTF-8");
                    content = content.replaceAll("\"version\"\\s*:\\s*\"[^\"]*\"", "\"version\":\"" + newVersion + "\"");
                    entries.put(name, content.getBytes("UTF-8"));
                    modified++;
                } catch (Exception ex) {}
            } else if (name.equals("version.json")) {
                try {
                    String content = new String(data, "UTF-8");
                    content = content.replaceAll("\"id\"\\s*:\\s*\"[^\"]*\"", "\"id\":\"" + newVersion + "\"");
                    entries.put(name, content.getBytes("UTF-8"));
                    modified++;
                } catch (Exception ex) {}
            } else if (name.equals("META-INF/MANIFEST.MF")) {
                try {
                    String content = new String(data, "UTF-8");
                    content = content.replaceAll("Implementation-Version:\\s*.+", "Implementation-Version: " + newVersion);
                    entries.put(name, content.getBytes("UTF-8"));
                    modified++;
                } catch (Exception ex) {}
            }
        }

        try (JarOutputStream jos = new JarOutputStream(new FileOutputStream(output))) {
            for (Map.Entry<String, byte[]> e : entries.entrySet()) {
                jos.putNextEntry(new JarEntry(e.getKey()));
                jos.write(e.getValue());
                jos.closeEntry();
            }
        }
        System.out.println("[VersionChanger] Modified " + modified + " files");
    }
}
