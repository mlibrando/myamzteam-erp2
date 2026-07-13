import "./globals.css";

export const metadata = {
  title: "P&L Dashboard",
  description: "MYAMZTEAM Amazon P&L — monthly grid",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased">{children}</body>
    </html>
  );
}
