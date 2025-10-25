import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const app = express();

// Serve static files from Vite build output
app.use(express.static(path.join(__dirname, "dist")));

// SPA fallback: route all unmatched requests to index.html
app.get("*", (_, res) => {
  res.sendFile(path.join(__dirname, "dist", "index.html"));
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`[SERVER] listening on port ${PORT}`));
