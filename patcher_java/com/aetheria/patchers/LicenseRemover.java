package com.aetheria.patchers;

import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import java.io.*;
import java.util.*;
import java.util.jar.*;

public class LicenseRemover {
    private static final String[] PATTERNS = {
        "checkLicense","verifyLicense","isLicensed","hasLicense",
        "validate","isValid","authenticate","isAuthenticated",
        "licenseKey","getLicense","verifyKey","checkKey",
        "isPremium","hasPremium","checkPremium","premium",
        "isCracked","hasCrack","checkCrack","cracked",
        "HWID","getHWID","getHardwareID","hardwareId",
        "deviceId","machineId","fingerprint","serial"
    };

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("Usage: java LicenseRemover <input.jar> <output.jar>");
            System.exit(1);
        }
        String input = args[0];
        String output = args[1];

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
            ClassReader cr = new ClassReader(e.getValue());
            ClassWriter cw = new ClassWriter(cr, ClassWriter.COMPUTE_MAXS);
            ClassVisitor cv = new ClassVisitor(Opcodes.ASM9, cw) {
                @Override
                public MethodVisitor visitMethod(int access, String name, String desc, String sig, String[] ex) {
                    return new MethodVisitor(Opcodes.ASM9, super.visitMethod(access, name, desc, sig, ex)) {
                        @Override
                        public void visitLdcInsn(Object value) {
                            if (value instanceof String) {
                                String s = (String) value;
                                for (String p : PATTERNS) {
                                    if (s.contains(p)) {
                                        super.visitLdcInsn("true");
                                        return;
                                    }
                                }
                            }
                            super.visitLdcInsn(value);
                        }

                        @Override
                        public void visitMethodInsn(int opcode, String owner, String name, String desc, boolean itf) {
                            for (String p : PATTERNS) {
                                if (name.contains(p) || owner.contains(p)) {
                                    super.visitInsn(Opcodes.ICONST_1);
                                    super.visitInsn(Opcodes.IRETURN);
                                    return;
                                }
                            }
                            super.visitMethodInsn(opcode, owner, name, desc, itf);
                        }
                    };
                }
            };
            cr.accept(cv, 0);
            classes.put(e.getKey(), cw.toByteArray());
            patched++;
        }

        try (JarOutputStream jos = new JarOutputStream(new FileOutputStream(output))) {
            for (Map.Entry<String, byte[]> e : classes.entrySet()) {
                jos.putNextEntry(new JarEntry(e.getKey()));
                jos.write(e.getValue());
                jos.closeEntry();
            }
        }
        System.out.println("Patched " + patched + " classes");
    }
}
