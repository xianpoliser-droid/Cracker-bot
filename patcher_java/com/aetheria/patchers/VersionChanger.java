package com.aetheria.patchers;

import java.io.*;
import java.util.*;
import java.util.jar.*;

public class VersionChanger {
    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.err.println("Usage: java VersionChanger <input.jar> <output.jar> <new_version>");
            System.exit(1);
        }
        String input = args[0];
        String output = args[1];
        String ver = args[2];

        Map<String, byte[]> entries = new LinkedHashMap<>();
        try (JarFile jar = new JarFile(input)) {
            Enumeration<JarEntry> en = jar.entries();
            while (en.hasMoreElements()) {
                JarEntry entry = en.nextElement();
                byte[] data = jar.getInputStream(entry).readAllBytes();
                entries.put(entry.getName(), data);
            }
        }

        int mod = 0;
        for (Map.Entry<String, byte[]> e : entries.entrySet()) {
            String name = e.getKey();
            byte[] data = e.getValue();
            if (name.equals("fabric.mod.json") || name.equals("fabric-mod.json")) {
                try {
                    String c = new String(data, "UTF-8");
                    c = c.replaceAll("\"version\"\\s*:\\s*\"[^\"]*\"", "\"version\":\"" + ver + "\"");
                    entries.put(name, c.getBytes("UTF-8"));
                    mod++;
                } catch (Exception ex) {}
            } else if (name.equals("version.json")) {
                try {
                    String c = new String(data, "UTF-8");
                    c = c.replaceAll("\"id\"\\s*:\\s*\"[^\"]*\"", "\"id\":\"" + ver + "\"");
                    entries.put(name, c.getBytes("UTF-8"));
                    mod++;
                } catch (Exception ex) {}
            } else if (name.equals("META-INF/MANIFEST.MF")) {
                try {
                    String c = new String(data, "UTF-8");
                    c = c.replaceAll("Implementation-Version:\\s*.+", "Implementation-Version: " + ver);
                    entries.put(name, c.getBytes("UTF-8"));
                    mod++;
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
        System.out.println("Modified " + mod + " files");
    }
}
