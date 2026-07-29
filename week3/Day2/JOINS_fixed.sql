--Q1: Query
SELECT c.first_name, c.last_name, c.email, ci.city, co.country
FROM customer c
JOIN address ad ON c.address_id = ad.address_id
JOIN city ci ON ad.city_id = ci.city_id
JOIN country co ON ci.country_id = co.country_id;
--Q2: Query
SELECT c.first_name, c.last_name, f.title, p.amount
FROM payment p
JOIN customer c ON p.customer_id = c.customer_id
JOIN rental r ON p.rental_id = r.rental_id
JOIN inventory i ON r.inventory_id = i.inventory_id
JOIN film f ON i.film_id = f.film_id;
--Q3: Query
SELECT c.first_name, c.last_name, SUM(p.amount) AS total_spent
FROM payment p
JOIN customer c ON p.customer_id = c.customer_id
GROUP BY c.first_name, c.last_name
ORDER BY total_spent DESC
LIMIT 10;
--Q4: Query
SELECT f.title, c.name, f.rental_rate
FROM film f
JOIN film_category ON f.film_id = film_category.film_id
JOIN category c ON film_category.category_id = c.category_id;
--Q5: Query
SELECT f.title, a.first_name, a.last_name
FROM film f
JOIN film_actor ON f.film_id = film_actor.film_id
JOIN actor a ON film_actor.actor_id = a.actor_id
ORDER BY f.title;
--Q6: Query
SELECT ct.name, COUNT(*) AS film_count
FROM film f
JOIN film_category ON f.film_id = film_category.film_id
JOIN category ct ON film_category.category_id = ct.category_id
GROUP BY ct.name
ORDER BY film_count DESC;
--Q7: Query
SELECT ct.name, SUM(p.amount) AS total_revenue
FROM category ct
JOIN film_category ON ct.category_id = film_category.category_id
JOIN film f ON film_category.film_id = f.film_id
JOIN inventory inv ON f.film_id = inv.film_id
JOIN rental r ON inv.inventory_id = r.inventory_id
JOIN payment p ON r.rental_id = p.rental_id
GROUP BY ct.name
ORDER BY total_revenue DESC;
--Q8: Query
SELECT cu.customer_id, cu.first_name, cu.last_name, COUNT(*) AS rental_count
FROM rental r
JOIN customer cu ON r.customer_id = cu.customer_id
GROUP BY cu.customer_id, cu.first_name, cu.last_name
HAVING COUNT(*) > 20
ORDER BY rental_count DESC;
--Q9: Query
SELECT ci.city, SUM(p.amount) AS total_revenue
FROM city ci
JOIN address ad ON ci.city_id = ad.city_id
JOIN customer cu ON ad.address_id = cu.address_id
JOIN payment p ON cu.customer_id = p.customer_id
GROUP BY ci.city
ORDER BY total_revenue DESC;
