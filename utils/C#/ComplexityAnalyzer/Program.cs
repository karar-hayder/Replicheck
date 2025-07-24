using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Newtonsoft.Json;

class FunctionInfo
{
    public required string Name { get; set; }
    public int Complexity { get; set; }
    public int LineNo { get; set; }
    public int EndLine { get; set; }
}

class Program
{
    static void Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.Error.WriteLine("Usage: dotnet run <path-to-cs-file>");
            return;
        }

        var filePath = args[0];
        if (!File.Exists(filePath))
        {
            Console.Error.WriteLine($"File not found: {filePath}");
            return;
        }

        var code = File.ReadAllText(filePath);
        var tree = CSharpSyntaxTree.ParseText(code);
        var root = tree.GetCompilationUnitRoot();

        var methods = root.DescendantNodes()
                          .OfType<MethodDeclarationSyntax>();

        var result = new List<FunctionInfo>();

        foreach (var method in methods)
        {
            var complexity = CalculateCyclomaticComplexity(method);
            var location = method.GetLocation().GetLineSpan();
            result.Add(new FunctionInfo
            {
                Name = method.Identifier.Text,
                Complexity = complexity,
                LineNo = location.StartLinePosition.Line + 1,
                EndLine = location.EndLinePosition.Line + 1
            });
        }

        Console.WriteLine(JsonConvert.SerializeObject(result, Formatting.None));
    }

    static int CalculateCyclomaticComplexity(MethodDeclarationSyntax method)
    {
        var walker = new ComplexityWalker();
        walker.Visit(method.Body);
        return walker.Complexity;
    }
}

class ComplexityWalker : CSharpSyntaxWalker
{
    public int Complexity { get; private set; } = 1; // Start with 1

    public override void VisitIfStatement(IfStatementSyntax node)
    {
        Complexity++;
        base.VisitIfStatement(node);
    }

    public override void VisitForStatement(ForStatementSyntax node)
    {
        Complexity++;
        base.VisitForStatement(node);
    }

    public override void VisitForEachStatement(ForEachStatementSyntax node)
    {
        Complexity++;
        base.VisitForEachStatement(node);
    }

    public override void VisitWhileStatement(WhileStatementSyntax node)
    {
        Complexity++;
        base.VisitWhileStatement(node);
    }

    public override void VisitDoStatement(DoStatementSyntax node)
    {
        Complexity++;
        base.VisitDoStatement(node);
    }

    public override void VisitCaseSwitchLabel(CaseSwitchLabelSyntax node)
    {
        Complexity++;
        base.VisitCaseSwitchLabel(node);
    }

    public override void VisitConditionalExpression(ConditionalExpressionSyntax node)
    {
        Complexity++;
        base.VisitConditionalExpression(node);
    }

    public override void VisitBinaryExpression(BinaryExpressionSyntax node)
    {
        if (node.IsKind(SyntaxKind.LogicalAndExpression) || node.IsKind(SyntaxKind.LogicalOrExpression))
        {
            Complexity++;
        }
        base.VisitBinaryExpression(node);
    }
}
