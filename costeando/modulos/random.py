def convertToBase13(num):
    if (num==0):
        return '0'
    else:
        resutaldo_parcial=num
        restos =[]
        while (resutaldo_parcial!=0):
            resto = str(resutaldo_parcial%13)
            resutaldo_parcial = (resutaldo_parcial//13)
            if(resto=='10'):
                resto= 'A'
            elif(resto=='11'):
                resto= 'B'
            elif(resto=='12'):
                resto= 'C'   
            restos.append(resto)

    return (''.join(reversed(restos)))
	
print(convertToBase13(69))