using System;

public class CheckStem
{
    private const int MAXAUGSTEMS = 12;
    private static bool init_stor = false;
    private static GkString[] tstemtab = new GkString[MAXAUGSTEMS];
    private static GkString[] tqstemtab = new GkString[MAXAUGSTEMS];
    private static string[] tkeytab = new string[MAXAUGSTEMS];

    public static int checkstem(string poss_stem, string endkeys, GkString[] stemtab, string[] keytab, int maxstems)
    {
        string curstemkeys = new string(new char[LONGSTRING + 1]);
        int hits = 0;
        int poss_augs = 0;
        int possno = 0;
        int rval = 0;

        if (!init_stor)
        {
            init_stor = true;
            for (int i = 0; i < MAXAUGSTEMS; i++)
            {
                tstemtab[i] = new GkString();
                tqstemtab[i] = new GkString();
                tkeytab[i] = new string(new char[LONGSTRING + 1]);
            }
        }
        for (int i = 0; i < MAXAUGSTEMS; i++)
        {
            tstemtab[i].Clear();
            tqstemtab[i].Clear();
            tkeytab[i] = string.Empty;
        }

        curstemkeys = string.Empty;
        rval = stemexists(poss_stem, endkeys, curstemkeys, 0);

        if (rval)
        {
            if (!string.IsNullOrEmpty(curstemkeys))
            {
                stemtab[possno].Set(poss_stem);
                keytab[possno] = curstemkeys;
                curstemkeys = string.Empty;
                possno++;
                hits++;
            }
        }

        if (IsCons(poss_stem[0]))
            goto finish;

        poss_augs = unaugment(poss_stem, tstemtab, tqstemtab, MAXAUGSTEMS, ALL_DIAL, 1, 0);

        for (int i = 0; i < poss_augs; i++)
        {
            curstemkeys = string.Empty;
            if (stemexists(tstemtab[i].Get(), endkeys, curstemkeys, 0))
            {
                if (!string.IsNullOrEmpty(curstemkeys))
                {
                    stemtab[hits] = tstemtab[i];
                    keytab[hits] = curstemkeys;
                    hits++;
                }
            }
        }

    finish:
        return hits;
    }

    public static int stemexists(string s, string endkeys, string stemkeys, int is_nom)
    {
        int rval = 0;

        rval = chckstem(s, stemkeys, is_nom);
        if (!rval && digstem)
        {
            longeststem(s);
        }

        if (!rval) return 0;

        rval = comstemtypes(s, stemkeys, endkeys);
        return rval;
    }

    public static int comstemtypes(string stem, string stemkeys, string endkeys)
    {
        string tmp = string.Empty;
        string cstemtype = string.Empty;
        string cstem = string.Empty;
        string clemma = string.Empty;
        string stembuf = string.Empty;

        string s = stemkeys;
        string p = tmp;

        stembuf = tmp = string.Empty;
        while (!string.IsNullOrEmpty(s))
        {
            setstemvars(s, cstem, clemma, cstemtype, stembuf);

            if (wantcurstemtype(cstemtype, endkeys))
            {
                if (!string.IsNullOrEmpty(tmp)) tmp += " ";
                tmp += clemma + ":" + (string.IsNullOrEmpty(cstem) ? stem : cstem) + ":" + cstemtype + ":" + stembuf;
            }
            while (!char.IsWhiteSpace(s[0]) && !string.IsNullOrEmpty(s)) s = s.Substring(1);
            while (char.IsWhiteSpace(s[0])) s = s.Substring(1);
        }
        stemkeys = p;

        return !string.IsNullOrEmpty(stemkeys) ? 1 : 0;
    }

    public static bool wantcurstemtype(string curst, string stlist)
    {
        return stlist.Contains(curst);
    }

    public static void setstemvars(string s, string cstem, string clemma, string cstemtype, string cstemkeys)
    {
        cstemkeys = cstem = clemma = cstemtype = string.Empty;

        s = parsefield(s, cstem, ':', MAXWORDSIZE);
        s = parsefield(s, clemma, ':', MAXWORDSIZE);
        s = parsefield(s, cstemtype, ':', MAXWORDSIZE);
        s = parsefield(s, cstemkeys, ' ', LONGSTRING);
    }

    public static string parsefield(string s, string buf, char c, int len)
    {
        buf = string.Empty;
        int i = 0;

        while (!string.IsNullOrEmpty(s) && s[0] != c && !char.IsWhiteSpace(s[0]))
        {
            buf += s[0];
            s = s.Substring(1);
            if (i++ >= len)
            {
                buf = string.Empty;
                while (!string.IsNullOrEmpty(s) && !char.IsWhiteSpace(s[0])) s = s.Substring(1);
                break;
            }
        }

        if (char.IsWhiteSpace(s[0])) return string.Empty;
        if (!string.IsNullOrEmpty(s)) s = s.Substring(1);
        return s;
    }

    public static void longeststem(string s)
    {
        string p = s;
        string tmp = s;
        string tmp2 = string.Empty;
        string stemkeys = string.Empty;
        int rval = 0;

        p = tmp;
        while (!string.IsNullOrEmpty(p)) p = p.Substring(0, p.Length - 1);
        while (p.Length >= tmp.Length)
        {
            tmp2 = p;
            p = p.Substring(0, p.Length - 1);
            if ((rval += chckstem(tmp, stemkeys, 1)) != 0)
            {
                Console.WriteLine($"{tmp}-{tmp2}\tn\t{stemkeys}");
            }
            if (chckstem(tmp, stemkeys, 0) != 0)
            {
                Console.WriteLine($"{tmp}-{tmp2}\tv\t{stemkeys}");
                break;
            }
            if (rval != 0) break;
        }
    }

    private static bool IsCons(char c)
    {
        return !IsVowel(c);
    }

    private static bool IsVowel(char c)
    {
        return "aeiouAEIOU".IndexOf(c) >= 0;
    }

    private static int chckstem(string s, string stemkeys, int is_nom)
    {
        // Placeholder for the actual implementation of chckstem
        return 0;
    }

    private static int unaugment(string poss_stem, GkString[] tstemtab, GkString[] tqstemtab, int maxaugstems, int all_dial, int v1, int v2)
    {
        // Placeholder for the actual implementation of unaugment
        return 0;
    }
}

public class GkString
{
    private string value;

    public GkString()
    {
        value = string.Empty;
    }

    public void Clear()
    {
        value = string.Empty;
    }

    public void Set(string val)
    {
        value = val;
    }

    public string Get()
    {
        return value;
    }
}
