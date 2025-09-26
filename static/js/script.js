// Custom JavaScript can be added here
console.log('ElMasa App loaded');

// Image fullscreen modal functionality
document.addEventListener('DOMContentLoaded', function () {
    // Create modal element
    const modal = document.createElement('div');
    modal.id = 'imageModal';
    modal.style.display = 'none';
    modal.style.position = 'fixed';
    modal.style.zIndex = '1050';
    modal.style.left = '0';
    modal.style.top = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.overflow = 'auto';
    modal.style.backgroundColor = 'rgba(0,0,0,0.9)';
    modal.style.cursor = 'pointer';

    // Create image element inside modal
    const modalImg = document.createElement('img');
    modalImg.style.margin = 'auto';
    modalImg.style.display = 'block';
    modalImg.style.maxWidth = '90%';
    modalImg.style.maxHeight = '90%';
    modalImg.style.marginTop = '5%';
    modal.appendChild(modalImg);

    // Append modal to body
    document.body.appendChild(modal);

    // When any image is clicked, open modal
    document.querySelectorAll('img').forEach(img => {
        img.style.cursor = 'zoom-in';
        img.addEventListener('click', function () {
            modal.style.display = 'block';
            modalImg.src = this.src;
        });
    });

    // When modal is clicked, close it
    modal.addEventListener('click', function () {
        modal.style.display = 'none';
    });
});
