"""Swarm intelligence optimizer - PSO and ACO for strategy parameter optimization."""
import logging
import numpy as np
from typing import Dict, List, Tuple, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Particle:
    """Represents a particle in PSO."""
    position: np.ndarray  # Strategy parameters
    velocity: np.ndarray
    best_position: np.ndarray
    best_fitness: float
    current_fitness: float = 0


class ParticleSwarmOptimizer:
    """Particle Swarm Optimization for parameter tuning."""

    def __init__(self, param_bounds: Dict[str, Tuple[float, float]],
                 population_size: int = 30, iterations: int = 50,
                 w: float = 0.7, c1: float = 1.5, c2: float = 1.5):
        """
        Initialize PSO.

        Args:
            param_bounds: Dict of parameter names to (min, max) tuples
            population_size: Number of particles
            iterations: Max iterations
            w: Inertia weight
            c1, c2: Cognitive and social coefficients
        """
        self.param_bounds = param_bounds
        self.param_names = list(param_bounds.keys())
        self.num_params = len(param_names)
        self.population_size = population_size
        self.iterations = iterations
        self.w = w  # Inertia weight
        self.c1 = c1  # Cognitive coefficient
        self.c2 = c2  # Social coefficient

        self.particles = self._initialize_particles()
        self.global_best_position = None
        self.global_best_fitness = -np.inf
        self.fitness_history = []

    def _initialize_particles(self) -> List[Particle]:
        """Initialize particles with random positions."""
        particles = []

        for _ in range(self.population_size):
            position = np.array([
                np.random.uniform(self.param_bounds[name][0],
                                 self.param_bounds[name][1])
                for name in self.param_names
            ])

            velocity = np.random.uniform(-1, 1, self.num_params)

            particle = Particle(
                position=position,
                velocity=velocity,
                best_position=position.copy(),
                best_fitness=-np.inf
            )

            particles.append(particle)

        return particles

    def optimize(self, fitness_func: Callable) -> Dict:
        """
        Run PSO optimization.

        Args:
            fitness_func: Function that takes parameter dict and returns fitness

        Returns:
            Optimization results
        """
        logger.info(f"Starting PSO with {self.population_size} particles for {self.iterations} iterations")

        for iteration in range(self.iterations):
            iteration_best_fitness = -np.inf

            # Evaluate fitness for each particle
            for particle in self.particles:
                # Convert position to parameter dict
                param_dict = self._position_to_params(particle.position)

                # Evaluate fitness
                fitness = fitness_func(param_dict)
                particle.current_fitness = fitness

                # Update personal best
                if fitness > particle.best_fitness:
                    particle.best_fitness = fitness
                    particle.best_position = particle.position.copy()

                # Update global best
                if fitness > self.global_best_fitness:
                    self.global_best_fitness = fitness
                    self.global_best_position = particle.position.copy()

                iteration_best_fitness = max(iteration_best_fitness, fitness)

            # Update velocities and positions
            for particle in self.particles:
                r1 = np.random.random(self.num_params)
                r2 = np.random.random(self.num_params)

                # PSO velocity update
                particle.velocity = (
                    self.w * particle.velocity +
                    self.c1 * r1 * (particle.best_position - particle.position) +
                    self.c2 * r2 * (self.global_best_position - particle.position)
                )

                # Update position
                particle.position += particle.velocity

                # Enforce bounds
                particle.position = np.clip(
                    particle.position,
                    [self.param_bounds[name][0] for name in self.param_names],
                    [self.param_bounds[name][1] for name in self.param_names]
                )

            self.fitness_history.append(self.global_best_fitness)

            if iteration % 10 == 0:
                logger.info(f"Iteration {iteration}: Best fitness = {self.global_best_fitness:.4f}")

        return {
            "best_params": self._position_to_params(self.global_best_position),
            "best_fitness": self.global_best_fitness,
            "history": self.fitness_history
        }

    def _position_to_params(self, position: np.ndarray) -> Dict[str, float]:
        """Convert particle position to parameter dictionary."""
        return {name: float(value) for name, value in zip(self.param_names, position)}


class AntColonyOptimizer:
    """Ant Colony Optimization for parameter discovery."""

    def __init__(self, param_bounds: Dict[str, Tuple[float, float]],
                 num_ants: int = 50, num_iterations: int = 50,
                 evaporation_rate: float = 0.1, alpha: float = 1.0, beta: float = 2.0):
        """
        Initialize ACO.

        Args:
            param_bounds: Dict of parameter names to (min, max) tuples
            num_ants: Number of ants
            num_iterations: Max iterations
            evaporation_rate: Pheromone evaporation rate
            alpha: Pheromone influence
            beta: Heuristic influence
        """
        self.param_bounds = param_bounds
        self.param_names = list(param_bounds.keys())
        self.num_params = len(param_names)
        self.num_ants = num_ants
        self.num_iterations = num_iterations
        self.evaporation_rate = evaporation_rate
        self.alpha = alpha  # Pheromone influence
        self.beta = beta  # Heuristic influence

        # Initialize pheromone trails for each parameter
        self.pheromone = {}
        self.best_solution = None
        self.best_fitness = -np.inf

    def optimize(self, fitness_func: Callable, discretization_levels: int = 10) -> Dict:
        """
        Run ACO optimization.

        Args:
            fitness_func: Function that takes parameter dict and returns fitness
            discretization_levels: Number of discrete levels per parameter

        Returns:
            Optimization results
        """
        logger.info(f"Starting ACO with {self.num_ants} ants for {self.num_iterations} iterations")

        # Initialize pheromone trails
        for param_name in self.param_names:
            self.pheromone[param_name] = np.ones(discretization_levels)

        fitness_history = []

        for iteration in range(self.num_iterations):
            # Each ant constructs a solution
            solutions = []
            fitnesses = []

            for _ in range(self.num_ants):
                # Ant constructs solution
                solution = {}
                for param_name in self.param_names:
                    min_val, max_val = self.param_bounds[param_name]

                    # Choose discrete level based on pheromone
                    pheromone_trail = self.pheromone[param_name]
                    probabilities = pheromone_trail ** self.alpha

                    # Add heuristic (uniform preference initially)
                    heuristic = np.ones(discretization_levels)
                    probabilities *= heuristic ** self.beta

                    probabilities /= probabilities.sum()

                    # Select discrete level
                    level = np.random.choice(discretization_levels, p=probabilities)

                    # Convert to actual value
                    value = min_val + (level / (discretization_levels - 1)) * (max_val - min_val)
                    solution[param_name] = float(value)

                solutions.append(solution)

                # Evaluate solution
                fitness = fitness_func(solution)
                fitnesses.append(fitness)

                # Update best
                if fitness > self.best_fitness:
                    self.best_fitness = fitness
                    self.best_solution = solution.copy()

            # Update pheromone based on best solutions
            fitness_array = np.array(fitnesses)
            best_idx = np.argmax(fitness_array)
            best_iter_solution = solutions[best_idx]
            best_iter_fitness = fitness_array[best_idx]

            # Evaporate pheromone
            for param_name in self.param_names:
                self.pheromone[param_name] *= (1 - self.evaporation_rate)

            # Deposit pheromone from best ants
            for idx in np.argsort(fitness_array)[-5:]:  # Top 5 ants
                solution = solutions[idx]
                fitness = fitnesses[idx]

                for param_name in self.param_names:
                    min_val, max_val = self.param_bounds[param_name]
                    value = solution[param_name]

                    # Find corresponding discrete level
                    level = int(discretization_levels * (value - min_val) / (max_val - min_val))
                    level = min(discretization_levels - 1, max(0, level))

                    # Deposit pheromone proportional to fitness
                    self.pheromone[param_name][level] += fitness / 100

            fitness_history.append(self.best_fitness)

            if iteration % 10 == 0:
                logger.info(f"Iteration {iteration}: Best fitness = {self.best_fitness:.4f}")

        return {
            "best_params": self.best_solution,
            "best_fitness": self.best_fitness,
            "history": fitness_history
        }


class HybridSwarmOptimizer:
    """Combines PSO and ACO for balanced optimization."""

    def __init__(self, param_bounds: Dict[str, Tuple[float, float]],
                 population_size: int = 30):
        """Initialize hybrid optimizer."""
        self.param_bounds = param_bounds
        self.pso = ParticleSwarmOptimizer(param_bounds, population_size)
        self.aco = AntColonyOptimizer(param_bounds, population_size)

    def optimize(self, fitness_func: Callable, iterations: int = 50) -> Dict:
        """
        Run hybrid PSO+ACO optimization.

        Args:
            fitness_func: Fitness function
            iterations: Number of iterations

        Returns:
            Best parameters and fitness
        """
        logger.info("Starting hybrid PSO+ACO optimization")

        # Phase 1: PSO exploration (60% of iterations)
        pso_iterations = int(iterations * 0.6)
        self.pso.iterations = pso_iterations
        pso_result = self.pso.optimize(fitness_func)

        # Phase 2: ACO refinement (40% of iterations)
        aco_iterations = iterations - pso_iterations
        aco_result = self.aco.optimize(fitness_func, discretization_levels=10)

        # Return best overall result
        best = pso_result if pso_result["best_fitness"] > aco_result["best_fitness"] else aco_result

        return {
            "best_params": best["best_params"],
            "best_fitness": best["best_fitness"],
            "pso_result": pso_result,
            "aco_result": aco_result,
            "combined_history": pso_result["history"] + aco_result["history"]
        }
