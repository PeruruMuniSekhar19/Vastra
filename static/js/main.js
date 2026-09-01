function searchProducts(){
  let input = document.getElementById('searchInput');
  let filter = input.value.toLowerCase();
  let cards = document.querySelectorAll('.product-card');
  cards.forEach(card=>{
    let name = card.dataset.name.toLowerCase();
    if(name.includes(filter)){
      card.style.display = "block";
    } else {
      card.style.display = "none";
    }
  });
}

function filterByCategory(cat){
  let cards = document.querySelectorAll('.product-card');
  let catLow = cat.toLowerCase();
  cards.forEach(card=>{
    let catData = (card.dataset.category || "").toLowerCase();
    let nameData = (card.dataset.name || "").toLowerCase();
    let combined = catData + "" + nameData;

    if(catLow==="all"){
      card.style.display = "block";
    }
    else if(catLow==="men"){
      if((combined.includes("men")|| catData.includes("men")) && !combined.includes("women")){
        card.style.display = "block";
      }else{
        card.style.display = "none";
      }
    }
    else if(catLow==="women"){
      card.style.display = combined.includes("women") || combined.includes("female") || catData.includes("saree") || catData.includes("gown") ? "block":"none";
    }
    else{
      card.style.display = combined.includes(catLow)? "block":"none";
    }
  });
}

function sortProducts(type){
  let grid = document.getElementById('shop-grid');
  let cards = Array.from(grid.querySelectorAll('.product-card'));
  cards.sort((a,b)=>{
    let pa = parseInt(a.dataset.price);
    let pb = parseInt(b.dataset.price);
    if(type==="low-high") return pa-pb;
    if(type==="high-low") return pb-pa;
    return 0;
  });
  cards.forEach(c=> grid.appendChild(c));
}

let cart = JSON.parse(localStorage.getItem('vastraCart') || '[]');
let el = document.getElementById('cart-count');
if(el) el.textContent = cart.length;
function toggleMenu(){
  let m=document.getElementById('mobileNav');
  m.style.display = (m.style.display==='flex') ? 'none' : 'flex';
}
function checkMobile(){
  let btn=document.getElementById('menuBtn');
  if(window.innerWidth < 768) btn.style.display='block';
  else { btn.style.display='none'; document.getElementById('mobileNav').style.display='none'; }
}
window.addEventListener('resize', checkMobile);
document.addEventListener('DOMContentLoaded', checkMobile);