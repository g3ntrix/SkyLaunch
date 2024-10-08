import oci
import time
import logging
import os
import json
from oci.config import from_file
from colorama import Fore, Style, init

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

CONFIG_FILE_PATH = "oci_config.json"

init(autoreset=True)

banner = """
░█▀▀░█░█░█░█░█░░░█▀█░█░█░█▀█░█▀▀░█░█
░▀▀█░█▀▄░░█░░█░░░█▀█░█░█░█░█░█░░░█▀█
░▀▀▀░▀░▀░░▀░░▀▀▀░▀░▀░▀▀▀░▀░▀░▀▀▀░▀░▀
"""


def print_banner():
    print(Fore.CYAN + banner)


def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def save_config(config):
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(config, f, indent=4)
    logger.info("Configuration saved to %s", CONFIG_FILE_PATH)


def load_config():
    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
        logger.info("Configuration loaded from %s", CONFIG_FILE_PATH)
        return config
    else:
        logger.info("No existing configuration found.")
        return {}


def view_config(compute_client, config):
    clear_screen()
    print_banner()
    print(Fore.GREEN + "\nCurrent Configuration:")
    for key, value in config.items():
        if key == "image_id":
            try:
                image = compute_client.get_image(value).data
                print(Fore.YELLOW + f"image_name: {image.display_name} (OCID: {value})")
            except oci.exceptions.ServiceError as e:
                logger.warning("Unable to retrieve image details: %s", e.message)
                print(Fore.YELLOW + f"{key}: {value}")
        elif key == "ssh_public_key":
            print(Fore.YELLOW + f"{key}: {'*' * 20}")  # Mask the SSH key
        else:
            print(Fore.YELLOW + f"{key}: {value}")
    input(Fore.CYAN + "\nPress Enter to return to the menu...")


def list_shapes(compute_client, compartment_id):
    logger.info("Fetching list of available shapes...")
    shapes = []
    list_shapes_response = compute_client.list_shapes(compartment_id, limit=50)
    shapes.extend(list_shapes_response.data)

    while list_shapes_response.has_next_page:
        list_shapes_response = compute_client.list_shapes(compartment_id, limit=50, page=list_shapes_response.next_page)
        shapes.extend(list_shapes_response.data)

    unique_shapes = {shape.shape: shape for shape in shapes}.values()

    return unique_shapes


def select_shape(shapes):
    clear_screen()
    print_banner()
    logger.info("Listing available shapes for selection:")
    for idx, shape in enumerate(shapes):
        print(Fore.YELLOW + f"{idx + 1}: {shape.shape} (OCPUs: {shape.ocpus}, Memory: {shape.memory_in_gbs} GB)")
    while True:
        try:
            shape_index = int(input(Fore.CYAN + "Select a shape by entering the corresponding number: ")) - 1
            if 0 <= shape_index < len(shapes):
                selected_shape = list(shapes)[shape_index]
                logger.info("Selected shape: %s", selected_shape.shape)
                return selected_shape.shape
            else:
                logger.warning("Invalid selection, please try again.")
        except ValueError:
            logger.warning("Invalid input, please enter a number.")


def list_images_by_shape(compute_client, compartment_id, shape):
    logger.info(f"Fetching list of available Ubuntu images for the selected shape: {shape}...")
    images = []
    list_images_response = compute_client.list_images(compartment_id, shape=shape, limit=50)
    images.extend(list_images_response.data)

    while list_images_response.has_next_page:
        list_images_response = compute_client.list_images(compartment_id, shape=shape, limit=50, page=list_images_response.next_page)
        images.extend(list_images_response.data)

    ubuntu_images = [image for image in images if 'Ubuntu' in image.display_name]

    if not ubuntu_images:
        logger.warning("No Ubuntu images found.")
    return ubuntu_images


def select_image(images):
    clear_screen()
    print_banner()
    logger.info("Listing available Ubuntu images for selection:")
    for idx, image in enumerate(images):
        print(Fore.YELLOW + f"{idx + 1}: {image.display_name}")
    while True:
        try:
            image_index = int(input(Fore.CYAN + "Select an image by entering the corresponding number: ")) - 1
            if 0 <= image_index < len(images):
                selected_image = images[image_index]
                logger.info("Selected image: %s", selected_image.display_name)
                return selected_image.id
            else:
                logger.warning("Invalid selection, please try again.")
        except ValueError:
            logger.warning("Invalid input, please enter a number.")


def initial_setup():
    clear_screen()
    print_banner()
    config = {}

    oci_config = load_oci_config()
    compute_client = oci.core.ComputeClient(oci_config)

    config['compartment_id'] = input("Enter the Compartment OCID: ")
    config['subnet_id'] = input("Enter the Subnet OCID: ")

    try:
        shapes = list_shapes(compute_client, config['compartment_id'])
    except oci.exceptions.ServiceError as e:
        logger.error("Error fetching shapes: %s", e.message)
        return

    shape = select_shape(shapes)
    config['shape'] = shape

    images = list_images_by_shape(compute_client, config['compartment_id'], shape)
    if images:
        image_id = select_image(images)
        config['image_id'] = image_id

    use_ssh = input("Do you want to use an SSH public key? (yes/no): ").strip().lower() == 'yes'
    if use_ssh:
        ssh_key_path = input("Enter the SSH public key file path (default: /root/id_rsa.pub): ").strip() or '/root/id_rsa.pub'
        try:
            with open(ssh_key_path, 'r') as f:
                config['ssh_public_key'] = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read SSH public key file: {e}")
            config['ssh_public_key'] = None
    else:
        config['ssh_public_key'] = None

    config['instance_name'] = input("Enter the instance name (default: Default-Instance): ") or 'Default-Instance'
    config['ocpus'] = int(input("Enter the number of OCPUs (default: 2): ") or 2)
    config['memory_in_gbs'] = int(input("Enter the memory in GBs (default: 12): ") or 12)

    save_config(config)


def create_instance(config, compartment_id, subnet_id, image_id, shape, ssh_public_key, ocpus, memory_in_gbs, instance_name, availability_domain):
    logger.info(f"Creating compute client for availability domain: {availability_domain}...")
    compute_client = oci.core.ComputeClient(config)

    logger.info("Setting up instance shape configuration...")
    shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
        ocpus=ocpus,
        memory_in_gbs=memory_in_gbs
    )

    logger.info("Preparing instance launch details...")
    metadata = {}
    if ssh_public_key:
        metadata['ssh_authorized_keys'] = ssh_public_key

    source_details = oci.core.models.InstanceSourceViaImageDetails(
        source_type="image",
        image_id=image_id,
        boot_volume_size_in_gbs=50
    )

    details = oci.core.models.LaunchInstanceDetails(
        compartment_id=compartment_id,
        availability_domain=availability_domain,
        subnet_id=subnet_id,
        shape=shape,
        shape_config=shape_config,
        display_name=instance_name,
        metadata=metadata,
        source_details=source_details
    )

    logger.info("Launching the instance...")
    try:
        response = compute_client.launch_instance(details)
        return response.data
    except oci.exceptions.ServiceError as e:
        logger.error(f"Service Error - Status: {e.status}")
        logger.error(f"Code: {e.code}")
        logger.error(f"Message: {e.message}")
        logger.error(f"Request ID: {e.request_id}")
        raise  # Re-raise the exception after logging


def load_oci_config():
    config_file = '/root/.oci/config'
    profile_name = 'DEFAULT'
    logger.info("Loading OCI configuration from file: %s, profile: %s", config_file, profile_name)
    return from_file(file_location=config_file, profile_name=profile_name)


def get_availability_domains(identity_client, compartment_id):
    logger.info("Fetching list of availability domains...")
    availability_domains = identity_client.list_availability_domains(compartment_id).data
    return [ad.name for ad in availability_domains]


def update_status_message(status_messages):
    clear_screen()
    print_banner()
    for message in status_messages:
        if "Out of host capacity" in message:
            print(Fore.RED + message + Style.RESET_ALL)
        else:
            print(Fore.GREEN + message + Style.RESET_ALL)


def report_resource_usage(compute_client, compartment_id):
    logger.info("Checking current instances and resource usage in account...")
    current_instance = compute_client.list_instances(compartment_id=compartment_id)
    response = current_instance.data

    total_ocpus = total_memory = micro_count = a1_flex_ocpus = a1_flex_memory = 0
    instance_names = []

    if response:
        logger.info(f"{len(response)} instance(s) found!")
        for instance in response:
            logger.info(
                f"{instance.display_name} - {instance.shape} - {int(instance.shape_config.ocpus)} ocpu(s) - {instance.shape_config.memory_in_gbs} GB(s) | State: {instance.lifecycle_state}")
            instance_names.append(instance.display_name)
            if instance.shape == "VM.Standard.E2.1.Micro" and instance.lifecycle_state not in ("TERMINATING", "TERMINATED"):
                micro_count += 1
            elif instance.shape == "VM.Standard.A1.Flex" and instance.lifecycle_state not in ("TERMINATING", "TERMINATED"):
                a1_flex_ocpus += int(instance.shape_config.ocpus)
                a1_flex_memory += int(instance.shape_config.memory_in_gbs)
        total_ocpus = a1_flex_ocpus
        total_memory = a1_flex_memory
        logger.info(f"Total A1 Flex OCPUs: {a1_flex_ocpus} - Total A1 Flex Memory: {a1_flex_memory} (GB)")
        logger.info(f"Total Micro Instances: {micro_count}")
    else:
        logger.info("No instances found!")

    return micro_count, total_ocpus, total_memory


def start_instance_creation_process():
    config = load_oci_config()
    user_config = load_config()

    compartment_id = user_config.get('compartment_id')
    subnet_id = user_config.get('subnet_id')
    ssh_public_key = user_config.get('ssh_public_key')
    instance_name = user_config.get('instance_name', 'Default-Instance')
    ocpus = user_config.get('ocpus', 2)
    memory_in_gbs = user_config.get('memory_in_gbs', 12)
    shape = user_config.get('shape')
    image_id = user_config.get('image_id')

    identity_client = oci.identity.IdentityClient(config)
    compute_client = oci.core.ComputeClient(config)
    availability_domains = get_availability_domains(identity_client, compartment_id)

    clear_screen()
    print_banner()

    micro_count, total_ocpus, total_memory = report_resource_usage(compute_client, compartment_id)

    if shape == "VM.Standard.E2.1.Micro" and micro_count >= 2:
        logger.critical("Exceeded the limit for VM.Standard.E2.1.Micro instances. **SCRIPT STOPPED**")
        input(Fore.RED + "\nPress Enter to return to the menu...")
        return

    if shape == "VM.Standard.A1.Flex" and (total_ocpus + ocpus > 4 or total_memory + memory_in_gbs > 24):
        logger.critical("Total maximum resource exceed free tier limit (Over 4 OCPUs/24GB total for A1 Flex). **SCRIPT STOPPED**")
        input(Fore.RED + "\nPress Enter to return to the menu...")
        return

    status_messages = []
    initial_sleep_time = 60
    max_sleep_time = 600
    sleep_time = initial_sleep_time
    total_count = 0
    rate_limit_retries = 0
    capacity_retries = 0

    try:
        while True:
            for ad in availability_domains:
                try:
                    status_messages.append(f"Attempting to create a new instance in availability domain {ad}...")
                    update_status_message(status_messages)
                    instance = create_instance(config, compartment_id, subnet_id, image_id, shape, ssh_public_key, ocpus, memory_in_gbs, instance_name, ad)
                    clear_screen()
                    print_banner()
                    print(Fore.GREEN + f"Successfully created instance {instance_name} with OCID {instance.id} in availability domain {ad}")
                    input(Fore.RED + "\nPress Enter to return to the menu...")
                    return

                except oci.exceptions.ServiceError as e:
                    total_count += 1
                    logger.error(f"Detailed error information:")
                    logger.error(f"Status: {e.status}")
                    logger.error(f"Code: {e.code}")
                    logger.error(f"Message: {e.message}")
                    logger.error(f"Request ID: {e.request_id}")

                    if e.status == 429:
                        rate_limit_retries += 1
                        status_messages.append(f"Rate limit reached, retry attempt {rate_limit_retries}.")
                    elif e.status == 500:
                        capacity_retries += 1
                        status_messages.append(Fore.RED + f"Out of host capacity in {ad}, retry attempt {capacity_retries}. Moving to next availability domain.")
                    else:
                        status_messages.append(f"Service error occurred: {e.message}")

                    update_status_message(status_messages)

                except Exception as e:
                    total_count += 1
                    status_messages.append(f"Unexpected error occurred: {str(e)}. Retrying...")
                    update_status_message(status_messages)

            status_messages.append(Fore.BLUE + f"Completed one round of retries in all availability domains. Next retry attempt in {sleep_time // 60} minutes..." + Style.RESET_ALL)
            update_status_message(status_messages)
            time.sleep(sleep_time)

            if rate_limit_retries > 0:
                sleep_time = min(max_sleep_time, sleep_time * 2)
            else:
                sleep_time = min(max_sleep_time, sleep_time + initial_sleep_time)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        input(Fore.RED + "\nPress Enter to return to the menu...")
def display_menu():
    clear_screen()
    print_banner()
    print(Fore.CYAN + "\nMenu:")
    print(Fore.CYAN + "1. Update Configuration")
    print(Fore.CYAN + "2. View Current Configuration")
    print(Fore.CYAN + "3. Start Instance Creation Process")
    print(Fore.CYAN + "4. Exit")
    choice = input(Fore.CYAN + "Enter your choice: ")
    return choice

def main():
    clear_screen()
    print_banner()
    if not os.path.exists(CONFIG_FILE_PATH):
        print(Fore.CYAN + "No configuration found. Starting initial setup.")
        initial_setup()

    oci_config = load_oci_config()
    compute_client = oci.core.ComputeClient(oci_config)

    while True:
        choice = display_menu()
        if choice == '1':
            initial_setup()
        elif choice == '2':
            config = load_config()
            view_config(compute_client, config)
        elif choice == '3':
            start_instance_creation_process()
        elif choice == '4':
            logger.info("Exiting the program.")
            break
        else:
            logger.warning("Invalid choice, please try again.")

if __name__ == "__main__":
    logger.info("Starting the instance creation process...")
    main()
    logger.info("Instance creation process completed.")