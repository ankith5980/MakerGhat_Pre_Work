import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Classroom Voice Analytics",
  description:
    "Offline-first classroom audio analytics MVP — transcription, teacher/student separation, and engagement metrics.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-lg text-white">
                🎙️
              </span>
              <div>
                <h1 className="text-lg font-semibold leading-tight">
                  Classroom Voice Analytics
                </h1>
                <p className="text-xs text-slate-500">
                  MakerGhat MVP · offline-first classroom insights
                </p>
              </div>
            </Link>
            <span className="hidden rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 sm:block">
              Whisper + speaker clustering · runs locally
            </span>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-400">
          MakerGhat Pre-Work · Task 1 · Classroom Analytics Prototype
        </footer>
      </body>
    </html>
  );
}
