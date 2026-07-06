import java.io.FileWriter;
import java.util.Scanner;

public class MissionControl {
    public static void main(String[] args) throws Exception {
        Scanner input = new Scanner(System.in);
        System.out.println(" MISSION CONTROL ONLINE");
        
        while (true) {
            System.out.println("\n--- Deploy Scientific Target Beacon ---");
            System.out.print("Enter Target X (-250 to 250): ");
            int x = input.nextInt();
            System.out.print("Enter Target Y (-250 to 250): ");
            int y = input.nextInt();

            // Write coordinates as "X,Y" to the shared text file
            FileWriter writer = new FileWriter("target.txt");
            writer.write(x + "," + y);
            writer.close();
            
            System.out.println("🛰️ Beacon deployed to coordinates! Transmission sent.");
        }
    }
}
