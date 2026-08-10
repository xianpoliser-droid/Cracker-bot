package com.aetheria.patchers;

import java.io.*;
import java.util.*;
import java.util.jar.*;
import java.util.regex.*;

public class URLDetector {
    private static final String[] PATTERNS = {
        "https?://[^\\s\"'<>]+",
        "(?:www\\.)[^\\s\"'<>]+",
        "[A-Za-z0-9.-]+\\.[A-Za-z]{2,}(?:/[^\\s\"']*)?"
    };

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: java URLDetector <input.jar>");
            System.exit(1);
        }
        String input = args[0];

        Set<String> urls = new LinkedHashSet<>();
        try (JarFile jar = new JarFile(input)) {
            Enumeration<JarEntry> entries = jar.entries();
            while (entries.hasMoreElements()) {
                JarEntry entry = entries.nextElement();
                String name = entry.getName();
                if (name.endsWith(".class") || name.endsWith(".json") || name.endsWith(".properties")) {
                    try (InputStream is = jar.getInputStream(entry)) {
                        String content = new String(is.readAllBytes(), "UTF-8");
                        for (String p : PATTERNS) {
                            Matcher m = Pattern.compile(p).matcher(content);
                            while (m.find()) {
                                urls.add(m.group());
                            }
                        }
                    } catch (Exception ignored) {}
                }
            }
        }

        System.out.println("[URLDetector] Found " + urls.size() + " URLs:");
        int i = 0;
        for (String url : urls) {
            if (i++ > 20) {
                System.out.println("... and " + (urls.size() - 20) + " more");
                break;
            }
            System.out.println("  " + url);
        }
    }
}
