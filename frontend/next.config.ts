import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Yjs deep imports (lib0/*, y-protocols/*) need transpilation under Turbopack.
  transpilePackages: ["yjs", "lib0", "y-protocols", "@tiptap/y-tiptap"],
  turbopack: {
    resolveAlias: {
      lib0: path.join(__dirname, "node_modules/lib0"),
      "y-protocols": path.join(__dirname, "node_modules/y-protocols"),
    },
  },
};

export default nextConfig;
