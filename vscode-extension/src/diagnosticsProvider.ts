/**
 * diagnosticsProvider.ts — Neo Bug Forge Code Action Provider
 * ─────────────────────────────────────────────────────────────
 * Registers a CodeActionsProvider so VS Code shows
 * "⚡ Fix with Neo Bug Forge" in the lightbulb menu for any
 * diagnostic (red/yellow squiggle).
 *
 * Respects the neo-bug-forge.diagnostics.enabled setting and
 * neo-bug-forge.diagnostics.severityThreshold (error | warning | all).
 */

import * as vscode from "vscode";

export class NbfCodeActionProvider implements vscode.CodeActionProvider {
  static readonly providedCodeActionKinds = [vscode.CodeActionKind.QuickFix];

  provideCodeActions(
    document: vscode.TextDocument,
    _range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext
  ): vscode.CodeAction[] {
    const cfg = vscode.workspace.getConfiguration("neo-bug-forge");

    // Respect the enabled toggle
    if (!cfg.get<boolean>("diagnostics.enabled", true)) {
      return [];
    }

    const threshold = cfg.get<string>("diagnostics.severityThreshold", "error");

    const actions: vscode.CodeAction[] = [];

    for (const diagnostic of context.diagnostics) {
      // Filter by severity
      if (!_shouldInclude(diagnostic.severity, threshold)) {
        continue;
      }

      const action = new vscode.CodeAction(
        "⚡ Fix with AI — Neo Bug Forge",
        vscode.CodeActionKind.QuickFix
      );

      action.command = {
        command: "neo-bug-forge.fixDiagnostic",
        title: "Fix with Neo Bug Forge",
        arguments: [document, diagnostic],
      };

      action.diagnostics = [diagnostic];
      // Don't mark as preferred — let the built-in quick fix stay preferred
      action.isPreferred = false;

      actions.push(action);
    }

    return actions;
  }
}

function _shouldInclude(
  severity: vscode.DiagnosticSeverity,
  threshold: string
): boolean {
  switch (threshold) {
    case "error":
      return severity === vscode.DiagnosticSeverity.Error;
    case "warning":
      return (
        severity === vscode.DiagnosticSeverity.Error ||
        severity === vscode.DiagnosticSeverity.Warning
      );
    case "all":
      return true;
    default:
      return severity === vscode.DiagnosticSeverity.Error;
  }
}
