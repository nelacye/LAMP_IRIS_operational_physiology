# Old-school R-style LAMP audit decision tree.
#
# Run with:
#   Rscript src/figures/make_lamp_audit_decision_tree_rstyle.R

out <- file.path("paper", "figures", "lamp_audit_decision_tree_rstyle.png")
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)

png(out, width = 3600, height = 1500, res = 300, bg = "white")
par(mar = c(1.8, 1.8, 1.8, 1.8), family = "serif", xaxs = "i", yaxs = "i")
plot.new()
plot.window(xlim = c(0, 1), ylim = c(0, 1))

box <- function(x, y, label, width, bold = FALSE) {
  rect(x - width / 2, y - 0.055, x + width / 2, y + 0.055, lwd = 1.2)
  text(x, y, label, cex = if (bold) 1.08 else 1.00, font = if (bold) 2 else 1)
}

arrow_right <- function(x1, x2, y) {
  arrows(x1, y, x2, y, length = 0.08, lwd = 1.1)
}

arrow_down <- function(x, y1, y2) {
  arrows(x, y1, x, y2, length = 0.08, lwd = 1.1)
}

main_y <- 0.68
x <- c(0.115, 0.33, 0.535, 0.74, 0.915)
widths <- c(0.185, 0.175, 0.170, 0.175, 0.095)
labels <- c("Latent-state claim", "Temporal isolation", "Matched cohorts", "Negative controls", "PASS")

for (i in seq_along(labels)) {
  box(x[i], main_y, labels[i], widths[i], bold = labels[i] %in% c("Latent-state claim", "PASS"))
}

for (i in 1:4) {
  arrow_right(x[i] + widths[i] / 2 + 0.006, x[i + 1] - widths[i + 1] / 2 - 0.006, main_y)
}

outcomes <- c("FAIL -> Leakage", "FAIL -> Shortcut", "FAIL -> Contamination")
fail_y <- 0.34
for (i in 1:3) {
  arrow_down(x[i + 1], main_y - 0.083, fail_y + 0.050)
  text(x[i + 1], fail_y, outcomes[i], cex = 0.90)
}

segments(0.31, 0.130, 0.69, 0.130, lwd = 1.0)
text(0.50, 0.065, "LAMP Audit Protocol", cex = 1.12, font = 2)

dev.off()
