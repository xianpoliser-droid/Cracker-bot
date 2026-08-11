package license_injector;

import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
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

        System.out.println("Key: " + key);

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

        // Find main class by scanning for main method signature
        for (Map.Entry<String, byte[]> e : classes.entrySet()) {
            try {
                ClassReader cr = new ClassReader(e.getValue());
                ClassNode cn = new ClassNode();
                cr.accept(cn, 0);
                for (MethodNode mn : cn.methods) {
                    if (mn.desc.equals("([Ljava/lang/String;)V") && mn.name.equals("main")) {
                        mainClass = e.getKey();
                        break;
                    }
                }
            } catch (Exception ignored) {}
            if (mainClass != null) break;
        }

        // Fallback: any class with methods
        if (mainClass == null) {
            for (Map.Entry<String, byte[]> e : classes.entrySet()) {
                try {
                    ClassReader cr = new ClassReader(e.getValue());
                    ClassNode cn = new ClassNode();
                    cr.accept(cn, 0);
                    if (!cn.methods.isEmpty()) {
                        mainClass = e.getKey();
                        break;
                    }
                } catch (Exception ignored) {}
                if (mainClass != null) break;
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
        ClassReader cr = new ClassReader(data);
        ClassWriter cw = new ClassWriter(cr, ClassWriter.COMPUTE_MAXS | ClassWriter.COMPUTE_FRAMES);
        ClassVisitor cv = new ClassVisitor(Opcodes.ASM9, cw) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String desc, String sig, String[] ex) {
                MethodVisitor mv = super.visitMethod(access, name, desc, sig, ex);
                if (name.equals("main") && desc.equals("([Ljava/lang/String;)V")) {
                    return new MethodVisitor(Opcodes.ASM9, mv) {
                        @Override
                        public void visitCode() {
                            // License check at start
                            mv.visitMethodInsn(Opcodes.INVOKESTATIC, "java/lang/System", "getProperty", "(Ljava/lang/String;)Ljava/lang/String;", false);
                            mv.visitLdcInsn("user.home");
                            mv.visitMethodInsn(Opcodes.INVOKESTATIC, "java/lang/System", "getProperty", "(Ljava/lang/String;)Ljava/lang/String;", false);
                            mv.visitLdcInsn("." + key.replace("-", "_") + "_license");
                            mv.visitTypeInsn(Opcodes.NEW, "java/io/File");
                            mv.visitInsn(Opcodes.DUP);
                            mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/io/File", "<init>", "(Ljava/lang/String;Ljava/lang/String;)V", false);
                            mv.visitVarInsn(Opcodes.ASTORE, 1);

                            Label exists = new Label();
                            mv.visitVarInsn(Opcodes.ALOAD, 1);
                            mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/io/File", "exists", "()Z", false);
                            mv.visitJumpInsn(Opcodes.IFNE, exists);

                            mv.visitFieldInsn(Opcodes.GETSTATIC, "java/lang/System", "out", "Ljava/io/PrintStream;");
                            mv.visitLdcInsn("LICENSE REQUIRED: " + key);
                            mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/io/PrintStream", "println", "(Ljava/lang/String;)V", false);
                            mv.visitInsn(Opcodes.ICONST_1);
                            mv.visitMethodInsn(Opcodes.INVOKESTATIC, "java/lang/System", "exit", "(I)V", false);

                            mv.visitLabel(exists);
                            mv.visitVarInsn(Opcodes.ALOAD, 1);
                            mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/io/File", "toPath", "()Ljava/nio/file/Path;", false);
                            mv.visitMethodInsn(Opcodes.INVOKESTATIC, "java/nio/file/Files", "readAllBytes", "(Ljava/nio/file/Path;)[B", false);
                            mv.visitTypeInsn(Opcodes.NEW, "java/lang/String");
                            mv.visitInsn(Opcodes.DUP);
                            mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/String", "<init>", "([B)V", false);
                            mv.visitVarInsn(Opcodes.ASTORE, 2);

                            Label valid = new Label();
                            mv.visitVarInsn(Opcodes.ALOAD, 2);
                            mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/lang/String", "trim", "()Ljava/lang/String;", false);
                            mv.visitLdcInsn(key);
                            mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/lang/String", "equals", "(Ljava/lang/Object;)Z", false);
                            mv.visitJumpInsn(Opcodes.IFNE, valid);

                            mv.visitFieldInsn(Opcodes.GETSTATIC, "java/lang/System", "out", "Ljava/io/PrintStream;");
                            mv.visitLdcInsn("INVALID LICENSE");
                            mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/io/PrintStream", "println", "(Ljava/lang/String;)V", false);
                            mv.visitInsn(Opcodes.ICONST_1);
                            mv.visitMethodInsn(Opcodes.INVOKESTATIC, "java/lang/System", "exit", "(I)V", false);

                            mv.visitLabel(valid);
                            super.visitCode();
                        }
                    };
                }
                return mv;
            }
        };
        cr.accept(cv, 0);
        classes.put(mainClass, cw.toByteArray());

        try (JarOutputStream jos = new JarOutputStream(new FileOutputStream(output))) {
            for (Map.Entry<String, byte[]> e : classes.entrySet()) {
                jos.putNextEntry(new JarEntry(e.getKey()));
                jos.write(e.getValue());
                jos.closeEntry();
            }
        }

        System.out.println("License injected into " + mainClass);
    }
}
