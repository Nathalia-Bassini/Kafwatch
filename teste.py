from network.NetworkScanner import NetworkScanner
from docker_manager.ComposeGenerator import ComposeGenerator
from docker_manager.ComposeManager import ComposeManager

if __name__ == "__main__":
    
    found_cameas = NetworkScanner(["10.145.80", "10.145.81", "10.145.82"], range(1, 255), 554, timeout=0.15)
    cameras = found_cameas.discover()

    docker_compose_gen = ComposeGenerator("admin", "Aluno@00")
    scan_results = {ip: [554] for ip in cameras}  # Todas as câmeras na porta 554
    docker_compose_gen.generate_files(scan_results)
    compose_manager = ComposeManager("docker_files/docker-compose.yml")
    compose_manager.up(build=True, detach=True)
    kafka_manager = ComposeManager("kafka/docker-compose.yml")
    kafka_manager.up(build=True, detach=True)
    