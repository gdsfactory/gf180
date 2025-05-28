window.setTimeout(function () {
    let new_url = location.href.replace('gf180', 'gf180mcu');
    console.log('Redirecting to', new_url);
    location.href = new_url;
}, 5000);
