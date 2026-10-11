import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.lm.registerMcpServerDefinitionProvider('ma2-onpc-mcp.mcp-servers', {
            provideMcpServerDefinitions: async () => [
                new vscode.McpStdioServerDefinition(
                    'MA2 Agent',
                    'uv',
                    ['run', 'python', '-m', 'src.server'],
                    {}, // Optionally pass .env variables here
                    '1.0.0'
                ),
                new vscode.McpStdioServerDefinition(
                    'time',
                    'uvx',
                    ['mcp-server-time'],
                    {},
                    '1.0.0'
                )
            ]
        })
    );
}

export function deactivate() {}
