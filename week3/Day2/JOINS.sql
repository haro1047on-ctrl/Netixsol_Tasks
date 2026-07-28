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
SELECT category.name, COUNT(*) AS film_count
FROM film
JOIN film_category ON film.film_id = film_category.film_id
JOIN category ON film_category.category_id = category.category_id
GROUP BY category.name
ORDER BY film_count DESC;
--Q7: Query
SELECT category.name, SUM(payment.amount) AS total_revenue
FROM category
JOIN film_category ON category.category_id = film_category.category_id
JOIN film ON film_category.film_id = film.film_id
JOIN inventory ON film.film_id = inventory.film_id
JOIN rental ON inventory.inventory_id = rental.inventory_id
JOIN payment ON rental.rental_id = payment.rental_id
GROUP BY category.name
ORDER BY total_revenue DESC;
--Q8: Query
SELECT customer.customer_id, customer.first_name, customer.last_name, COUNT(*) AS rental_count
FROM rental
JOIN customer ON rental.customer_id = customer.customer_id
GROUP BY customer.customer_id, customer.first_name, customer.last_name
HAVING COUNT(*) > 20
ORDER BY rental_count DESC;
--Q9: Query
SELECT city.city, SUM(payment.amount) AS total_revenue
FROM city
JOIN address ON city.city_id = address.city_id
JOIN customer ON address.address_id = customer.address_id
JOIN payment ON customer.customer_id = payment.customer_id
GROUP BY city.city
ORDER BY total_revenue DESC;