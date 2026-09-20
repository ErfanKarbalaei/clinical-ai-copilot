import type { Metadata } from "next";

import { DirectionProvider } from "@/components/ui/direction";

import "vazirmatn/Vazirmatn-Variable-font-face.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Clinical AI Copilot",
    template: "%s | Clinical AI Copilot",
  },
  description: "دستیار هوشمند بالینی برای پزشکان",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // The whole application is Persian and right-to-left (RTL).
    <html lang="fa" dir="rtl" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">
        <DirectionProvider direction="rtl">{children}</DirectionProvider>
      </body>
    </html>
  );
}
