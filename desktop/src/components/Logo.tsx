import logoImg from "../assets/logo.png";

export default function Logo({ size = 24 }: { size?: number }) {
  return <img src={logoImg} alt="Nexus" width={size} height={size} style={{ borderRadius: size * 0.18 }} />;
}
