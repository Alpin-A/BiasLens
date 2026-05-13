import type { Metadata } from "next";
import "./globals.css";
import { ThemeToggle } from "@/components/theme-toggle";

export const metadata: Metadata = {
  title: "BiasLens – Trading Behavior Analysis",
  description:
    "AI-powered trading behavior analysis. Detect biases, simulate corrections, get coaching.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('theme');
                  if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                    document.documentElement.classList.add('dark');
                  }
                } catch(e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-screen bg-background font-sans antialiased transition-colors duration-300">
        <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
          <div className="container flex h-12 items-center px-6">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center">
                <span className="text-white text-sm font-bold">B</span>
              </div>
              <span className="font-bold text-lg tracking-tight">
                Bias<span className="text-gradient">Lens</span>
              </span>
            </div>
            <nav className="ml-auto flex items-center gap-4 text-sm text-muted-foreground">
              <span className="hidden sm:inline">AI Trading Behavior Analysis</span>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="container mx-auto px-6 py-5 max-w-[1400px]">
          {children}
        </main>
      </body>
    </html>
  );
}
