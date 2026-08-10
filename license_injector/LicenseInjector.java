package license_injector;

import java.io.*;
import java.util.*;
import java.util.jar.*;

public class LicenseInjector {
    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.err.println("Usage: java LicenseInjector <input.jar> <output.jar> <license_key>");
            System.exit(1);
        }

        String input = args[0];
        String output = args[1];
        String key = args[2];

        System.out.println("License key: " + key);

        Map<String, byte[]> classes = new LinkedHashMap<>();
        String mainClass = null;

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

        for (String name : classes.keySet()) {
            if (name.contains("Main") || name.contains("Client") || name.contains("Launcher")) {
                mainClass = name;
                break;
            }
        }
        if (mainClass == null && !classes.isEmpty()) {
            mainClass = classes.keySet().iterator().next();
        }

        if (mainClass == null) {
            System.err.println("No class found");
            System.exit(1);
        }

        System.out.println("Main class: " + mainClass);

        byte[] data = classes.get(mainClass);
        String content = new String(data, "UTF-8");
        String check = "try { java.io.File f = new java.io.File(System.getProperty(\"user.home\"), \".license\"); if (!f.exists()) { System.out.println(\"LICENSE REQUIRED: " + key + "\"); System.exit(1); } String c = new String(java.nio.file.Files.readAllBytes(f.toPath())); if (!c.trim().equals(\"" + key + "\")) { System.out.println(\"INVALID LICENSE\"); System.exit(1); } } catch (Exception e) { System.out.println(\"LICENSE ERROR\"); System.exit(1); }";
        content = content.replace("public static void main", "public static void __main");
        content = content.replace("public class", "public static void main(String[] a) { " + check + " __main(a); } public class");
        classes.put(mainClass, content.getBytes("UTF-8"));

        try (JarOutputStream jos = new JarOutputStream(new FileOutputStream(output))) {
            for (Map.Entry<String, byte[]> e : classes.entrySet()) {
                jos.putNextEntry(new JarEntry(e.getKey()));
                jos.write(e.getValue());
                jos.closeEntry();
            }
        }

        System.out.println("License injected");
    }
}
