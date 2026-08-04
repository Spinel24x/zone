// Hexagon background animation
const canvas = document.getElementById('hexCanvas');
if (canvas) {
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const hexSize = 40;
    const hexWidth = hexSize * 2;
    const hexHeight = Math.sqrt(3) * hexSize;
    let offset = 0;

    function drawHex(x, y, size) {
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 6;
            const hx = x + size * Math.cos(angle);
            const hy = y + size * Math.sin(angle);
            if (i === 0) ctx.moveTo(hx, hy);
            else ctx.lineTo(hx, hy);
        }
        ctx.closePath();
        ctx.strokeStyle = 'rgba(0, 255, 136, 0.15)';
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        offset = (offset + 0.2) % (hexHeight * 2);
        
        for (let row = -1; row < canvas.height / hexHeight + 1; row++) {
            for (let col = -1; col < canvas.width / hexWidth + 1; col++) {
                const x = col * hexWidth * 0.75;
                const y = row * hexHeight + (col % 2 === 0 ? 0 : hexHeight / 2) + offset;
                drawHex(x, y, hexSize);
            }
        }
        requestAnimationFrame(animate);
    }

    animate();

    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}
