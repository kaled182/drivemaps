 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/app/logging_config.py b/app/logging_config.py
new file mode 100644
index 0000000000000000000000000000000000000000..39af44a18442d5f4f749e292012dce55a7eae26c
--- /dev/null
+++ b/app/logging_config.py
@@ -0,0 +1,28 @@
+"""Configuração centralizada de logging para a aplicação DriveMaps."""
+
+import logging
+from pathlib import Path
+
+
+LOG_FILE = Path('app.log')
+
+
+def configure_logging(level: int = logging.INFO) -> None:
+    """Configura o logging apenas uma vez, evitando handlers duplicados."""
+    root_logger = logging.getLogger()
+    if root_logger.handlers:
+        return
+
+    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
+
+    logging.basicConfig(
+        level=level,
+        format='%(asctime)s - %(levelname)s - %(message)s',
+        handlers=[
+            logging.StreamHandler(),
+            logging.FileHandler(LOG_FILE)
+        ]
+    )
+
+
+__all__ = ["configure_logging"]
 
EOF
)
