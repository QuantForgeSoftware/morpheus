using System;
using System.IO;

public class Betamorph
{
    public static int quickflag;
    public static string anal_buf()
    {
        // Placeholder for the actual implementation of anal_buf
        return string.Empty;
    }

    public static void Main(string[] args)
    {
        string line;
        PrntFlags prntflags = PrntFlags.KEEP_BETA;
        string s;
        int nverbs = 0;
        int rval;

        while ((line = Console.ReadLine()) != null)
        {
            if (!line.StartsWith(":le:"))
            {
                continue;
            }
            s = line.Substring(4);
            rval = checkstring(s, prntflags);
            Console.WriteLine($"{s}\t{rval}");
            if (++nverbs > 10) break;
        }
    }

    public static int checkstring(string s, PrntFlags prntflags)
    {
        // Placeholder for the actual implementation of checkstring
        return 0;
    }
}

[Flags]
public enum PrntFlags
{
    KEEP_BETA = 1
}
