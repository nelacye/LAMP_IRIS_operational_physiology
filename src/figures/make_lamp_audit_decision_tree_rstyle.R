# Old-school R-style LAMP audit decision tree.
#
# Run with:
#   Rscript src/figures/make_lamp_audit_decision_tree_rstyle.R

out <- file.path("paper", "figures", "lamp_audit_decision_tree_rstyle.png")
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)

png(out, width = 2200, height = 2800, res = 300, bg = "white")
par(mar = c(1.8, 1.8, 1.8, 1.8), family = "serif", xaxs = "i", yaxs = "i")
plot.new()
plot.window(xlim = c(0, 1), ylim = c(0, 1))

box <- function(x, y, label, bold = FALSE) {
  rect(x - 0.18, y - 0.030, x + 0.18, y + 0.030, lwd = 1.2)
  text(x, y, label, cex = if (bold) 1.15 else 1.05, font = if (bold) 2 else 1)
}

arrow_down <- function(x, y1, y2) {
  arrows(x, y1, x, y2, length = 0.08, lwd = 1.1)
}

arrow_right <- function(x1, x2, y) {
  arrows(x1, y, x2, y, length = 0.08, lwd = 1.1)
}

x <- 0.34
y <- c(0.88, 0.68, 0.48, 0.28, 0.10)
labels <- c("Latent-state claim", "Temporal isolation", "Matched cohorts", "Negative controls", "PASS")

for (i in seq_along(labels)) {
  box(x, y[i], labels[i], bold = labels[i] %in% c("Latent-state claim", "PASS"))
}

for (i in 1:4) {
  arrow_down(x, y[i] - 0.055, y[i + 1] + 0.055)
}

outcomes <- c("FAIL -> Leakage", "FAIL -> Shortcut", "FAIL -> Contamination")
for (i in 1:3) {
  yy <- y[i + 1]
  arrow_right(x + 0.20, 0.58, yy)
  text(0.62, yy, outcomes[i], adj = c(0, 0.5), cex = 1.02)
}

segments(0.26, 0.035, 0.74, 0.035, lwd = 1.0)
text(0.50, 0.015, "LAMP Audit Protocol", cex = 1.18, font = 2)

dev.off()
