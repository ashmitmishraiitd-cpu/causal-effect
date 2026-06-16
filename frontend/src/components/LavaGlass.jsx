import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshTransmissionMaterial } from '@react-three/drei';
import { useRef } from 'react';

function GlassSphere({ position, args, color, speed }) {
  const ref = useRef();
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.rotation.x = clock.getElapsedTime() * speed * 0.3;
      ref.current.rotation.y = clock.getElapsedTime() * speed * 0.4;
    }
  });
  return (
    <Float speed={1.2} rotationIntensity={0.2} floatIntensity={0.3}>
      <mesh ref={ref} position={position}>
        <icosahedronGeometry args={args} />
        <MeshTransmissionMaterial
          backside
          backsideThickness={0.3}
          thickness={0.5}
          chromaticAberration={0.06}
          roughness={0.05}
          metalness={0}
          color={color}
          transparent
          opacity={0.5}
        />
      </mesh>
    </Float>
  );
}

export default function LavaGlass() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 50 }}
        dpr={[1, 1.5]}
        gl={{ alpha: false, antialias: true }}
        style={{ background: '#0a0a0f', width: '100%', height: '100%' }}
      >
        <ambientLight intensity={0.6} />
        <pointLight position={[4, 4, 4]} intensity={2} color="#e63946" />
        <pointLight position={[-4, -2, 3]} intensity={1.5} color="#f87171" />
        <pointLight position={[0, -4, 2]} intensity={0.8} color="#b71c1c" />
        <GlassSphere position={[0, 0.5, 0]} args={[1.6, 2]} color="#e63946" speed={0.8} />
        <GlassSphere position={[-2.8, -1.5, -1.5]} args={[1.0, 2]} color="#f87171" speed={0.5} />
        <GlassSphere position={[2.6, -1.2, -2]} args={[1.2, 2]} color="#d62828" speed={0.6} />
        <GlassSphere position={[0.5, 2.5, -3]} args={[0.7, 1]} color="#b71c1c" speed={0.4} />
      </Canvas>
    </div>
  );
}
